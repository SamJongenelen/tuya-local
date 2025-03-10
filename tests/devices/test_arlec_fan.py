from homeassistant.components.fan import (
    DIRECTION_FORWARD,
    DIRECTION_REVERSE,
    SUPPORT_DIRECTION,
    SUPPORT_PRESET_MODE,
    SUPPORT_SET_SPEED,
)

from homeassistant.const import STATE_UNAVAILABLE

from ..const import ARLEC_FAN_PAYLOAD
from ..helpers import assert_device_properties_set
from .base_device_tests import TuyaDeviceTestCase

SWITCH_DPS = "1"
SPEED_DPS = "3"
DIRECTION_DPS = "4"
PRESET_DPS = "102"
TIMER_DPS = "103"


class TestArlecFan(TuyaDeviceTestCase):
    __test__ = True

    def setUp(self):
        self.setUpForConfig("arlec_fan.yaml", ARLEC_FAN_PAYLOAD)
        self.subject = self.entities["fan"]

    def test_supported_features(self):
        self.assertEqual(
            self.subject.supported_features,
            SUPPORT_DIRECTION | SUPPORT_PRESET_MODE | SUPPORT_SET_SPEED,
        )

    def test_is_on(self):
        self.dps[SWITCH_DPS] = True
        self.assertTrue(self.subject.is_on)

        self.dps[SWITCH_DPS] = False
        self.assertFalse(self.subject.is_on)

        self.dps[SWITCH_DPS] = None
        self.assertEqual(self.subject.is_on, STATE_UNAVAILABLE)

    async def test_turn_on(self):
        async with assert_device_properties_set(
            self.subject._device, {SWITCH_DPS: True}
        ):
            await self.subject.async_turn_on()

    async def test_turn_off(self):
        async with assert_device_properties_set(
            self.subject._device, {SWITCH_DPS: False}
        ):
            await self.subject.async_turn_off()

    def test_preset_mode(self):
        self.dps[PRESET_DPS] = "normal"
        self.assertEqual(self.subject.preset_mode, "normal")

        self.dps[PRESET_DPS] = "breeze"
        self.assertEqual(self.subject.preset_mode, "breeze")

        self.dps[PRESET_DPS] = "sleep"
        self.assertEqual(self.subject.preset_mode, "sleep")

        self.dps[PRESET_DPS] = None
        self.assertIs(self.subject.preset_mode, None)

    def test_preset_modes(self):
        self.assertCountEqual(self.subject.preset_modes, ["normal", "breeze", "sleep"])

    async def test_set_preset_mode_to_normal(self):
        async with assert_device_properties_set(
            self.subject._device,
            {PRESET_DPS: "normal"},
        ):
            await self.subject.async_set_preset_mode("normal")

    async def test_set_preset_mode_to_breeze(self):
        async with assert_device_properties_set(
            self.subject._device,
            {PRESET_DPS: "breeze"},
        ):
            await self.subject.async_set_preset_mode("breeze")

    async def test_set_preset_mode_to_sleep(self):
        async with assert_device_properties_set(
            self.subject._device,
            {PRESET_DPS: "sleep"},
        ):
            await self.subject.async_set_preset_mode("sleep")

    def test_direction(self):
        self.dps[DIRECTION_DPS] = "forward"
        self.assertEqual(self.subject.current_direction, DIRECTION_FORWARD)
        self.dps[DIRECTION_DPS] = "reverse"
        self.assertEqual(self.subject.current_direction, DIRECTION_REVERSE)

    async def test_set_direction_forward(self):
        async with assert_device_properties_set(
            self.subject._device, {DIRECTION_DPS: "forward"}
        ):
            await self.subject.async_set_direction(DIRECTION_FORWARD)

    async def test_set_direction_reverse(self):
        async with assert_device_properties_set(
            self.subject._device, {DIRECTION_DPS: "reverse"}
        ):
            await self.subject.async_set_direction(DIRECTION_REVERSE)

    def test_speed(self):
        self.dps[SPEED_DPS] = "3"
        self.assertEqual(self.subject.percentage, 50)

    def test_speed_step(self):
        self.assertAlmostEqual(self.subject.percentage_step, 16.67, 2)
        self.assertEqual(self.subject.speed_count, 6)

    async def test_set_speed(self):
        async with assert_device_properties_set(self.subject._device, {SPEED_DPS: 2}):
            await self.subject.async_set_percentage(33)

    async def test_set_speed_in_normal_mode_snaps(self):
        self.dps[PRESET_DPS] = "normal"
        async with assert_device_properties_set(self.subject._device, {SPEED_DPS: 5}):
            await self.subject.async_set_percentage(80)

    def test_device_state_attributes(self):
        self.dps[TIMER_DPS] = "2hour"
        self.assertEqual(self.subject.device_state_attributes, {"timer": "2hour"})
