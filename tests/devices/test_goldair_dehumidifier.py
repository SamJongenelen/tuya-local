from unittest import skip
from unittest.mock import ANY

from homeassistant.components.climate.const import (
    FAN_HIGH,
    FAN_LOW,
    HVAC_MODE_DRY,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_HUMIDITY,
)
from homeassistant.components.light import COLOR_MODE_ONOFF
from homeassistant.components.lock import STATE_LOCKED, STATE_UNLOCKED
from homeassistant.const import STATE_UNAVAILABLE

from ..const import DEHUMIDIFIER_PAYLOAD
from ..helpers import assert_device_properties_set
from .base_device_tests import TuyaDeviceTestCase

HVACMODE_DPS = "1"
PRESET_DPS = "2"
HUMIDITY_DPS = "4"
AIRCLEAN_DPS = "5"
FANMODE_DPS = "6"
LOCK_DPS = "7"
ERROR_DPS = "11"
UNKNOWN12_DPS = "12"
UNKNOWN101_DPS = "101"
LIGHTOFF_DPS = "102"
CURRENTTEMP_DPS = "103"
CURRENTHUMID_DPS = "104"
DEFROST_DPS = "105"

PRESET_NORMAL = "0"
PRESET_LOW = "1"
PRESET_HIGH = "2"
PRESET_DRY_CLOTHES = "3"

ERROR_TANK = "Tank full or missing"


class TestGoldairDehumidifier(TuyaDeviceTestCase):
    __test__ = True

    def setUp(self):
        self.setUpForConfig("goldair_dehumidifier.yaml", DEHUMIDIFIER_PAYLOAD)
        self.subject = self.entities.get("humidifier")
        self.fan = self.entities.get("fan")
        self.climate = self.entities.get("climate")
        self.light = self.entities.get("light")
        self.lock = self.entities.get("lock")
        self.switch = self.entities.get("switch")

    def test_supported_features(self):
        self.assertEqual(
            self.climate.supported_features,
            SUPPORT_TARGET_HUMIDITY | SUPPORT_PRESET_MODE | SUPPORT_FAN_MODE,
        )

    def test_icon_is_always_standard_when_off_without_error(self):
        self.dps[ERROR_DPS] = None
        self.dps[HVACMODE_DPS] = False

        self.dps[AIRCLEAN_DPS] = False
        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.icon, "mdi:air-humidifier-off")

        self.dps[AIRCLEAN_DPS] = True
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.assertEqual(self.climate.icon, "mdi:air-humidifier-off")

    def test_icon_is_purifier_when_air_clean_is_active(self):
        self.dps[ERROR_DPS] = None
        self.dps[HVACMODE_DPS] = True
        self.dps[AIRCLEAN_DPS] = True
        self.assertEqual(self.climate.icon, "mdi:air-purifier")

    def test_icon_is_tshirt_when_dry_clothes_is_active(self):
        self.dps[ERROR_DPS] = None
        self.dps[HVACMODE_DPS] = True
        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.icon, "mdi:tshirt-crew-outline")

    def test_icon_is_always_melting_snowflake_when_defrosting_and_tank_not_full(self):
        self.dps[DEFROST_DPS] = True

        self.dps[HVACMODE_DPS] = False
        self.assertEqual(self.climate.icon, "mdi:snowflake-melt")

        self.dps[HVACMODE_DPS] = True
        self.assertEqual(self.climate.icon, "mdi:snowflake-melt")

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.icon, "mdi:snowflake-melt")

        self.dps[AIRCLEAN_DPS] = True
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.assertEqual(self.climate.icon, "mdi:snowflake-melt")

    def test_icon_is_always_tank_when_tank_full_error_is_present(self):
        self.dps[ERROR_DPS] = 8

        self.dps[HVACMODE_DPS] = False
        self.assertEqual(self.climate.icon, "mdi:cup-water")

        self.dps[HVACMODE_DPS] = True
        self.assertEqual(self.climate.icon, "mdi:cup-water")

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.icon, "mdi:cup-water")

        self.dps[AIRCLEAN_DPS] = True
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.assertEqual(self.climate.icon, "mdi:cup-water")

        self.dps[DEFROST_DPS] = True
        self.assertEqual(self.climate.icon, "mdi:cup-water")

    def test_current_humidity(self):
        self.dps[CURRENTHUMID_DPS] = 47
        self.assertEqual(self.climate.current_humidity, 47)

    def test_min_target_humidity(self):
        self.assertEqual(self.climate.min_humidity, 30)
        self.assertEqual(self.subject.min_humidity, 30)

    def test_max_target_humidity(self):
        self.assertEqual(self.climate.max_humidity, 80)
        self.assertEqual(self.subject.max_humidity, 80)

    def test_target_humidity_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.dps[HUMIDITY_DPS] = 55

        self.assertEqual(self.climate.target_humidity, 55)

    def test_target_humidity_in_humidifier(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.dps[HUMIDITY_DPS] = 45

        self.assertEqual(self.subject.target_humidity, 45)

    def test_target_humidity_outside_normal_preset(self):
        self.dps[HUMIDITY_DPS] = 55

        self.dps[PRESET_DPS] = PRESET_HIGH
        self.assertIs(self.climate.target_humidity, None)

        self.dps[PRESET_DPS] = PRESET_LOW
        self.assertIs(self.climate.target_humidity, None)

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertIs(self.climate.target_humidity, None)

        # self.dps[PRESET_DPS] = PRESET_NORMAL
        # self.dps[AIRCLEAN_DPS] = True
        # self.assertIs(self.climate.target_humidity, None)

    async def test_set_target_humidity_in_normal_preset_rounds_up_to_5_percent(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.climate._device,
            {HUMIDITY_DPS: 55},
        ):
            await self.climate.async_set_humidity(53)

    async def test_set_target_humidity_in_normal_preset_rounds_down_to_5_percent(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL

        async with assert_device_properties_set(
            self.climate._device,
            {HUMIDITY_DPS: 50},
        ):
            await self.climate.async_set_humidity(52)

    async def test_set_humidity_in_humidifier_rounds_up_to_5_percent(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.subject._device,
            {HUMIDITY_DPS: 45},
        ):
            await self.subject.async_set_humidity(43)

    async def test_set_humidity_in_humidifier_rounds_down_to_5_percent(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.subject._device,
            {HUMIDITY_DPS: 40},
        ):
            await self.subject.async_set_humidity(42)

    async def test_set_target_humidity_raises_error_outside_of_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_LOW
        with self.assertRaisesRegex(
            AttributeError, "humidity cannot be set at this time"
        ):
            await self.climate.async_set_humidity(50)

        self.dps[PRESET_DPS] = PRESET_HIGH
        with self.assertRaisesRegex(
            AttributeError, "humidity cannot be set at this time"
        ):
            await self.climate.async_set_humidity(50)

        self.dps[PRESET_DPS] = PRESET_LOW
        with self.assertRaisesRegex(
            AttributeError, "humidity cannot be set at this time"
        ):
            await self.climate.async_set_humidity(50)

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        with self.assertRaisesRegex(
            AttributeError, "humidity cannot be set at this time"
        ):
            await self.climate.async_set_humidity(50)

        # self.dps[PRESET_DPS] = PRESET_NORMAL
        # self.dps[AIRCLEAN_DPS] = True
        # with self.assertRaisesRegex(
        #     AttributeError, "humidity cannot be set at this time"
        # ):
        #     await self.climate.async_set_humidity(50)

    def test_temperature_unit_returns_device_temperature_unit(self):
        self.assertEqual(
            self.climate.temperature_unit, self.climate._device.temperature_unit
        )

    def test_minimum_target_temperature(self):
        self.assertIs(self.climate.min_temp, None)

    def test_maximum_target_temperature(self):
        self.assertIs(self.climate.max_temp, None)

    def test_current_temperature(self):
        self.dps[CURRENTTEMP_DPS] = 25
        self.assertEqual(self.climate.current_temperature, 25)

    def test_hvac_mode(self):
        self.dps[HVACMODE_DPS] = True
        self.assertEqual(self.climate.hvac_mode, HVAC_MODE_DRY)

        self.dps[HVACMODE_DPS] = False
        self.assertEqual(self.climate.hvac_mode, HVAC_MODE_OFF)

        self.dps[HVACMODE_DPS] = None
        self.assertEqual(self.climate.hvac_mode, STATE_UNAVAILABLE)

    def test_hvac_modes(self):
        self.assertCountEqual(self.climate.hvac_modes, [HVAC_MODE_OFF, HVAC_MODE_DRY])

    async def test_turn_on(self):
        async with assert_device_properties_set(
            self.climate._device, {HVACMODE_DPS: True}
        ):
            await self.climate.async_set_hvac_mode(HVAC_MODE_DRY)

    async def test_turn_off(self):

        async with assert_device_properties_set(
            self.climate._device, {HVACMODE_DPS: False}
        ):
            await self.climate.async_set_hvac_mode(HVAC_MODE_OFF)

    def test_humidifier_is_on(self):
        self.dps[HVACMODE_DPS] = True
        self.assertTrue(self.subject.is_on)

        self.dps[HVACMODE_DPS] = False
        self.assertFalse(self.subject.is_on)

    async def test_dehumidifier_turn_on(self):
        async with assert_device_properties_set(
            self.subject._device, {HVACMODE_DPS: True}
        ):
            await self.subject.async_turn_on()

    async def test_dehumidifier_turn_off(self):
        async with assert_device_properties_set(
            self.subject._device, {HVACMODE_DPS: False}
        ):
            await self.subject.async_turn_off()

    def test_preset_mode(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.assertEqual(self.climate.preset_mode, "Normal")
        self.assertEqual(self.subject.mode, "Normal")

        self.dps[PRESET_DPS] = PRESET_LOW
        self.assertEqual(self.climate.preset_mode, "Low")
        self.assertEqual(self.subject.mode, "Low")

        self.dps[PRESET_DPS] = PRESET_HIGH
        self.assertEqual(self.climate.preset_mode, "High")
        self.assertEqual(self.subject.mode, "High")

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.preset_mode, "Dry clothes")
        self.assertEqual(self.subject.mode, "Dry clothes")

        self.dps[PRESET_DPS] = None
        self.assertEqual(self.climate.preset_mode, None)
        self.assertEqual(self.subject.mode, None)

    def test_air_clean_is_surfaced_in_preset_mode(self):
        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.dps[AIRCLEAN_DPS] = True

        self.assertEqual(self.climate.preset_mode, "Air clean")

    def test_preset_modes(self):
        self.assertCountEqual(
            self.climate.preset_modes,
            [
                "Normal",
                "Low",
                "High",
                "Dry clothes",
                "Air clean",
            ],
        )

    async def test_set_preset_mode_to_normal(self):
        async with assert_device_properties_set(
            self.climate._device,
            {
                PRESET_DPS: PRESET_NORMAL,
                AIRCLEAN_DPS: False,
            },
        ):
            await self.climate.async_set_preset_mode("Normal")
            self.climate._device.anticipate_property_value.assert_not_called()

    async def test_set_preset_mode_to_low(self):
        async with assert_device_properties_set(
            self.climate._device,
            {
                PRESET_DPS: PRESET_LOW,
                AIRCLEAN_DPS: False,
            },
        ):
            await self.climate.async_set_preset_mode("Low")

            # No anticipation of device behaviour in generic implementation
            # self.climate._device.anticipate_property_value.assert_called_once_with(
            #     FANMODE_DPS, "1"
            # )

    async def test_set_preset_mode_to_high(self):
        async with assert_device_properties_set(
            self.climate._device,
            {
                PRESET_DPS: PRESET_HIGH,
                AIRCLEAN_DPS: False,
            },
        ):
            await self.climate.async_set_preset_mode("High")

            # No anticipation of device behaviour in generic implementation
            # self.climate._device.anticipate_property_value.assert_called_once_with(
            #     FANMODE_DPS, "3"
            # )

    async def test_set_preset_mode_to_dry_clothes(self):
        async with assert_device_properties_set(
            self.climate._device,
            {
                PRESET_DPS: PRESET_DRY_CLOTHES,
                AIRCLEAN_DPS: False,
            },
        ):
            await self.climate.async_set_preset_mode("Dry clothes")

            # No anticipation of device behaviour in generic implementation
            # self.climate._device.anticipate_property_value.assert_called_once_with(
            #     FANMODE_DPS, "3"
            # )

    async def test_set_preset_mode_to_air_clean(self):
        async with assert_device_properties_set(
            self.climate._device, {AIRCLEAN_DPS: True, PRESET_DPS: ANY}
        ):
            await self.climate.async_set_preset_mode("Air clean")

            # No anticipation of device behaviour in generic implementation
            # self.climate._device.anticipate_property_value.assert_called_once_with(
            #     FANMODE_DPS, "1"
            # )

    @skip("Conditions not included in config")
    def test_fan_mode_is_forced_to_high_in_high_dry_clothes_air_clean_presets(self):
        self.dps[FANMODE_DPS] = "1"
        self.dps[PRESET_DPS] = PRESET_HIGH
        self.assertEqual(self.climate.fan_mode, FAN_HIGH)
        self.assertEqual(self.fan.percentage, 100)

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.fan_mode, FAN_HIGH)
        self.assertEqual(self.fan.percentage, 100)

        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.dps[AIRCLEAN_DPS] = True
        self.assertEqual(self.climate.fan_mode, FAN_HIGH)
        self.assertEqual(self.climate.percentage, 100)

    @skip("Conditions not included in config")
    def test_fan_mode_is_forced_to_low_in_low_preset(self):
        self.dps[FANMODE_DPS] = "3"
        self.dps[PRESET_DPS] = PRESET_LOW

        self.assertEqual(self.climate.fan_mode, FAN_LOW)
        self.assertEqual(self.fan.percentage, 50)

    def test_fan_mode_reflects_dps_mode_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.dps[FANMODE_DPS] = "1"
        self.assertEqual(self.climate.fan_mode, FAN_LOW)
        self.assertEqual(self.fan.percentage, 50)

        self.dps[FANMODE_DPS] = "3"
        self.assertEqual(self.climate.fan_mode, FAN_HIGH)
        self.assertEqual(self.fan.percentage, 100)

        self.dps[FANMODE_DPS] = None
        self.assertEqual(self.climate.fan_mode, None)
        self.assertEqual(self.fan.percentage, None)

    @skip("Conditions not included in config")
    def test_fan_modes_reflect_preset_mode(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        self.assertCountEqual(self.climate.fan_modes, [FAN_LOW, FAN_HIGH])
        self.assertEqual(self.fan.speed_count, 2)

        self.dps[PRESET_DPS] = PRESET_LOW
        self.assertEqual(self.climate.fan_modes, [FAN_LOW])
        self.assertEqual(self.fan.speed_count, 0)

        self.dps[PRESET_DPS] = PRESET_HIGH
        self.assertEqual(self.climate.fan_modes, [FAN_HIGH])
        self.assertEqual(self.fan.speed_count, 0)

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        self.assertEqual(self.climate.fan_modes, [FAN_HIGH])
        self.assertEqual(self.fan.speed_count, 0)

        # self.dps[PRESET_DPS] = PRESET_NORMAL
        # self.dps[AIRCLEAN_DPS] = True
        # self.assertEqual(self.climate.fan_modes, [FAN_HIGH])
        # self.assertEqual(self.fan.speed_count, 0)

    async def test_set_fan_mode_to_low_succeeds_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.climate._device,
            {FANMODE_DPS: "1"},
        ):
            await self.climate.async_set_fan_mode(FAN_LOW)

    async def test_set_fan_mode_to_high_succeeds_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.climate._device,
            {FANMODE_DPS: "3"},
        ):
            await self.climate.async_set_fan_mode(FAN_HIGH)

    async def test_set_fan_50_succeeds_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.fan._device,
            {FANMODE_DPS: "1"},
        ):
            await self.fan.async_set_percentage(50)

    async def test_set_fan_100_succeeds_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.fan._device,
            {FANMODE_DPS: "3"},
        ):
            await self.fan.async_set_percentage(100)

    async def test_set_fan_30_snaps_to_50_in_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        async with assert_device_properties_set(
            self.fan._device,
            {FANMODE_DPS: "1"},
        ):
            await self.fan.async_set_percentage(30)

    @skip("Restriction to listed options not supported yet")
    async def test_set_fan_mode_fails_with_invalid_mode(self):
        self.dps[PRESET_DPS] = PRESET_NORMAL
        with self.assertRaisesRegex(ValueError, "Invalid fan mode: something"):
            await self.climate.async_set_fan_mode("something")

    @skip("Conditions not yet supported for setting")
    async def test_set_fan_mode_fails_outside_normal_preset(self):
        self.dps[PRESET_DPS] = PRESET_LOW
        with self.assertRaisesRegex(
            AttributeError, "fan_mode cannot be set at this time"
        ):
            await self.climate.async_set_fan_mode(FAN_HIGH)

        self.dps[PRESET_DPS] = PRESET_HIGH
        with self.assertRaisesRegex(
            AttributeError, "fan_mode cannot be set at this time"
        ):
            await self.climate.async_set_fan_mode(FAN_HIGH)

        self.dps[PRESET_DPS] = PRESET_DRY_CLOTHES
        with self.assertRaisesRegex(
            AttributeError, "fan_mode cannot be set at this time"
        ):
            await self.climate.async_set_fan_mode(FAN_HIGH)

        # self.dps[PRESET_DPS] = PRESET_NORMAL
        # self.dps[AIRCLEAN_DPS] = True
        # with self.assertRaisesRegex(
        #     ValueError, "Fan mode can only be changed while in Normal preset mode"
        # ):
        #     await self.climate.async_set_fan_mode(FAN_HIGH)

    def test_device_state_attributes(self):
        self.dps[ERROR_DPS] = None
        self.dps[DEFROST_DPS] = False
        self.dps[AIRCLEAN_DPS] = False
        self.dps[UNKNOWN12_DPS] = "something"
        self.dps[UNKNOWN101_DPS] = False
        self.assertDictEqual(
            self.climate.device_state_attributes,
            {
                "error": None,
                "defrosting": False,
                "air_clean_on": False,
                "unknown_12": "something",
                "unknown_101": False,
            },
        )

        self.dps[ERROR_DPS] = 8
        self.dps[DEFROST_DPS] = True
        self.dps[AIRCLEAN_DPS] = True
        self.dps[UNKNOWN12_DPS] = "something else"
        self.dps[UNKNOWN101_DPS] = True
        self.assertDictEqual(
            self.climate.device_state_attributes,
            {
                "error": ERROR_TANK,
                "defrosting": True,
                "air_clean_on": True,
                "unknown_12": "something else",
                "unknown_101": True,
            },
        )

    def test_lock_state(self):
        self.dps[LOCK_DPS] = True
        self.assertEqual(self.lock.state, STATE_LOCKED)

        self.dps[LOCK_DPS] = False
        self.assertEqual(self.lock.state, STATE_UNLOCKED)

        self.dps[LOCK_DPS] = None
        self.assertEqual(self.lock.state, STATE_UNAVAILABLE)

    def test_lock_is_locked(self):
        self.dps[LOCK_DPS] = True
        self.assertTrue(self.lock.is_locked)

        self.dps[LOCK_DPS] = False
        self.assertFalse(self.lock.is_locked)

        self.dps[LOCK_DPS] = None
        self.assertFalse(self.lock.is_locked)

    async def test_lock_locks(self):
        async with assert_device_properties_set(self.lock._device, {LOCK_DPS: True}):
            await self.lock.async_lock()

    async def test_lock_unlocks(self):
        async with assert_device_properties_set(self.lock._device, {LOCK_DPS: False}):
            await self.lock.async_unlock()

    def test_light_supported_color_modes(self):
        self.assertCountEqual(
            self.light.supported_color_modes,
            [COLOR_MODE_ONOFF],
        )

    def test_light_color_mode(self):
        self.assertEqual(self.light.color_mode, COLOR_MODE_ONOFF)

    def test_light_icon(self):
        self.dps[LIGHTOFF_DPS] = False
        self.assertEqual(self.light.icon, "mdi:led-on")

        self.dps[LIGHTOFF_DPS] = True
        self.assertEqual(self.light.icon, "mdi:led-off")

    def test_light_is_on(self):
        self.dps[LIGHTOFF_DPS] = False
        self.assertEqual(self.light.is_on, True)

        self.dps[LIGHTOFF_DPS] = True
        self.assertEqual(self.light.is_on, False)

    def test_light_state_attributes(self):
        self.assertEqual(self.light.device_state_attributes, {})

    async def test_light_turn_on(self):
        async with assert_device_properties_set(
            self.light._device, {LIGHTOFF_DPS: False}
        ):
            await self.light.async_turn_on()

    async def test_light_turn_off(self):
        async with assert_device_properties_set(
            self.light._device, {LIGHTOFF_DPS: True}
        ):
            await self.light.async_turn_off()

    async def test_toggle_turns_the_light_on_when_it_was_off(self):
        self.dps[LIGHTOFF_DPS] = True

        async with assert_device_properties_set(
            self.light._device, {LIGHTOFF_DPS: False}
        ):
            await self.light.async_toggle()

    async def test_toggle_turns_the_light_off_when_it_was_on(self):
        self.dps[LIGHTOFF_DPS] = False

        async with assert_device_properties_set(
            self.light._device, {LIGHTOFF_DPS: True}
        ):
            await self.light.async_toggle()

    def test_switch_icon(self):
        self.assertEqual(self.switch.icon, "mdi:air-purifier")

    def test_switch_is_on(self):
        self.dps[AIRCLEAN_DPS] = True
        self.assertEqual(self.switch.is_on, True)

        self.dps[AIRCLEAN_DPS] = False
        self.assertEqual(self.switch.is_on, False)

    def test_switch_state_attributes(self):
        self.assertEqual(self.switch.device_state_attributes, {})

    async def test_switch_turn_on(self):
        async with assert_device_properties_set(
            self.switch._device, {AIRCLEAN_DPS: True}
        ):
            await self.switch.async_turn_on()

    async def test_switch_turn_off(self):
        async with assert_device_properties_set(
            self.switch._device, {AIRCLEAN_DPS: False}
        ):
            await self.switch.async_turn_off()

    async def test_toggle_turns_the_switch_on_when_it_was_off(self):
        self.dps[AIRCLEAN_DPS] = False

        async with assert_device_properties_set(
            self.switch._device, {AIRCLEAN_DPS: True}
        ):
            await self.switch.async_toggle()

    async def test_toggle_turns_the_switch_off_when_it_was_on(self):
        self.dps[AIRCLEAN_DPS] = True

        async with assert_device_properties_set(
            self.switch._device, {AIRCLEAN_DPS: False}
        ):
            await self.switch.async_toggle()
