"""
Config parser for Tuya Local devices.
"""
from fnmatch import fnmatch
import logging
from os import walk
from os.path import join, dirname, splitext, exists
from pydoc import locate

from homeassistant.util.yaml import load_yaml

import custom_components.tuya_local.devices as config_dir

_LOGGER = logging.getLogger(__name__)


def _typematch(type, value):
    # Workaround annoying legacy of bool being a subclass of int in Python
    if type is int and isinstance(value, bool):
        return False

    if isinstance(value, type):
        return True
    # Allow values embedded in strings if they can be converted
    # But not for bool, as everything can be converted to bool
    elif isinstance(value, str) and type is not bool:
        try:
            type(value)
            return True
        except ValueError:
            return False
    return False


def _scale_range(r, s):
    "Scale range r by factor s"
    if s == 1:
        return r
    return {"min": r["min"] / s, "max": r["max"] / s}


class TuyaDeviceConfig:
    """Representation of a device config for Tuya Local devices."""

    def __init__(self, fname):
        """Initialize the device config.
        Args:
            fname (string): The filename of the yaml config to load."""
        _CONFIG_DIR = dirname(config_dir.__file__)
        self._fname = fname
        filename = join(_CONFIG_DIR, fname)
        self._config = load_yaml(filename)
        _LOGGER.debug("Loaded device config %s", fname)

    @property
    def name(self):
        """Return the friendly name for this device."""
        return self._config["name"]

    @property
    def config(self):
        """Return the config file associated with this device."""
        return self._fname

    @property
    def config_type(self):
        """Return the config type associated with this device."""
        return splitext(self._fname)[0]

    @property
    def legacy_type(self):
        """Return the legacy conf_type associated with this device."""
        return self._config.get("legacy_type", self.config_type)

    @property
    def primary_entity(self):
        """Return the primary type of entity for this device."""
        return TuyaEntityConfig(self, self._config["primary_entity"])

    def secondary_entities(self):
        """Iterate through entites for any secondary entites supported."""
        for conf in self._config.get("secondary_entities", {}):
            yield TuyaEntityConfig(self, conf)

    def matches(self, dps):
        """Determine if this device matches the provided dps map."""
        for d in self.primary_entity.dps():
            if d.id not in dps.keys() or not _typematch(d.type, dps[d.id]):
                return False

        for dev in self.secondary_entities():
            for d in dev.dps():
                if d.id not in dps.keys() or not _typematch(d.type, dps[d.id]):
                    return False
        _LOGGER.debug("Matched config for %s", self.name)
        return True

    def _entity_match_analyse(self, entity, keys, matched, dps):
        """
        Determine whether this entity can be a match for the dps
          Args:
            entity - the TuyaEntityConfig to check against
            keys - the unmatched keys for the device
            matched - the matched keys for the device
            dps - the dps values to be matched
        Side Effects:
            Moves items from keys to matched if they match dps
        Return Value:
            True if all dps in entity could be matched to dps, False otherwise
        """
        for d in entity.dps():
            if (d.id not in keys and d.id not in matched) or not _typematch(
                d.type, dps[d.id]
            ):
                return False
            if d.id in keys:
                matched.append(d.id)
                keys.remove(d.id)
        return True

    def match_quality(self, dps):
        """Determine the match quality for the provided dps map."""
        keys = list(dps.keys())
        matched = []
        if "updated_at" in keys:
            keys.remove("updated_at")
        total = len(keys)
        if not self._entity_match_analyse(self.primary_entity, keys, matched, dps):
            return 0

        for e in self.secondary_entities():
            if not self._entity_match_analyse(e, keys, matched, dps):
                return 0

        return round((total - len(keys)) * 100 / total)


class TuyaEntityConfig:
    """Representation of an entity config for a supported entity."""

    def __init__(self, device, config):
        self._device = device
        self._config = config

    @property
    def name(self):
        """The friendly name for this entity."""
        own_name = self._config.get("name")
        if own_name is None:
            return self._device.name
        else:
            return self._device.name + " " + own_name

    @property
    def legacy_class(self):
        """Return the legacy device corresponding to this config."""
        name = self._config.get("legacy_class")
        if name is None:
            return None
        return locate("custom_components.tuya_local" + name)

    @property
    def deprecated(self):
        """Return whether this entitiy is deprecated."""
        return "deprecated" in self._config.keys()

    @property
    def deprecation_message(self):
        """Return a deprecation message for this entity"""
        replacement = self._config.get(
            "deprecated", "nothing, this warning has been raised in error"
        )
        return (
            f"The use of {self.entity} for {self._device.name} is "
            f"deprecated and should be replaced by {replacement}."
        )

    @property
    def entity(self):
        """The entity type of this entity."""
        return self._config["entity"]

    @property
    def config_id(self):
        """The identifier for this entitiy in the config."""
        return self.entity

    @property
    def device_class(self):
        """The device class of this entity."""
        return self._config.get("class")

    def icon(self, device):
        """Return the icon for this device, with state as given."""
        icon = self._config.get("icon", None)
        priority = self._config.get("icon_priority", 100)

        for d in self.dps():
            rule = d.icon_rule(device)
            if rule and rule["priority"] < priority:
                icon = rule["icon"]
                priority = rule["priority"]
        return icon

    def dps(self):
        """Iterate through the list of dps for this entity."""
        for d in self._config["dps"]:
            yield TuyaDpsConfig(self, d)

    def find_dps(self, name):
        """Find a dps with the specified name."""
        for d in self.dps():
            if d.name == name:
                return d
        return None


class TuyaDpsConfig:
    """Representation of a dps config."""

    def __init__(self, entity, config):
        self._entity = entity
        self._config = config
        self.stringify = False

    @property
    def id(self):
        return str(self._config["id"])

    @property
    def type(self):
        t = self._config["type"]
        types = {
            "boolean": bool,
            "integer": int,
            "string": str,
            "float": float,
            "bitfield": int,
        }
        return types.get(t)

    @property
    def name(self):
        return self._config["name"]

    def get_value(self, device):
        """Return the value of the dps from the given device."""
        return self._map_from_dps(device.get_property(self.id), device)

    async def async_set_value(self, device, value):
        """Set the value of the dps in the given device to given value."""
        if self.readonly:
            raise TypeError(f"{self.name} is read only")
        if self.invalid_for(value, device):
            raise AttributeError(f"{self.name} cannot be set at this time")

        settings = self.get_values_to_set(device, value)
        await device.async_set_properties(settings)

    def values(self, device):
        """Return the possible values a dps can take."""
        if "mapping" not in self._config.keys():
            _LOGGER.debug(
                f"No mapping for {self.name}, unable to determine valid values"
            )
            return None
        val = []
        for m in self._config["mapping"]:
            if "value" in m:
                val.append(m["value"])
            for c in m.get("conditions", {}):
                if "value" in c:
                    val.append(c["value"])
            cond = self._active_condition(m, device)
            if cond and "mapping" in cond:
                _LOGGER.debug("Considering conditional mappings")
                c_val = []
                for m2 in cond["mapping"]:
                    if "value" in m2:
                        c_val.append(m2["value"])
                # if given, the conditional mapping is an override
                if c_val:
                    _LOGGER.debug(f"Overriding {self.name} values {val} with {c_val}")
                    val = c_val
                    break
        _LOGGER.debug(f"{self.name} values: {val}")
        return list(set(val)) if val else None

    def range(self, device, scaled=True):
        """Return the range for this dps if configured."""
        mapping = self._find_map_for_dps(device.get_property(self.id))
        scale = 1
        if mapping:
            _LOGGER.debug(f"Considering mapping for range of {self.name}")
            if scaled:
                scale = mapping.get("scale", scale)
            cond = self._active_condition(mapping, device)
            if cond:
                constraint = mapping.get("constraint")
                if scaled:
                    scale = mapping.get("scale", scale)
                _LOGGER.debug(f"Considering condition on {constraint}")
            r = None if cond is None else cond.get("range")
            if r and "min" in r and "max" in r:
                _LOGGER.info(f"Conditional range returned for {self.name}")
                return _scale_range(r, scale)
            r = mapping.get("range")
            if r and "min" in r and "max" in r:
                _LOGGER.info(f"Mapped range returned for {self.name}")
                return _scale_range(r, scale)
        r = self._config.get("range")
        if r and "min" in r and "max" in r:
            return _scale_range(r, scale)
        else:
            return None

    def step(self, device, scaled=True):
        step = 1
        scale = 1
        mapping = self._find_map_for_dps(device.get_property(self.id))
        if mapping:
            _LOGGER.debug(f"Considering mapping for step of {self.name}")
            step = mapping.get("step", 1)
            scale = mapping.get("scale", 1)
            cond = self._active_condition(mapping, device)
            if cond:
                constraint = mapping.get("constraint")
                _LOGGER.debug(f"Considering condition on {constraint}")
                step = cond.get("step", step)
                scale = cond.get("scale", scale)
        if step != 1 or scale != 1:
            _LOGGER.info(f"Step for {self.name} is {step} with scale {scale}")
        return step / scale if scaled else step

    @property
    def readonly(self):
        return self._config.get("readonly", False)

    def invalid_for(self, value, device):
        mapping = self._find_map_for_value(value)
        if mapping:
            cond = self._active_condition(mapping, device)
            if cond:
                return cond.get("invalid", False)
        return False

    @property
    def hidden(self):
        return self._config.get("hidden", False)

    @property
    def unit(self):
        return self._config.get("unit")

    def _find_map_for_dps(self, value):
        default = None
        for m in self._config.get("mapping", {}):
            if "dps_val" not in m:
                default = m
            elif str(m["dps_val"]) == str(value):
                return m
        return default

    def _map_from_dps(self, value, device):
        if value is not None and self.type is not str and isinstance(value, str):
            try:
                value = self.type(value)
                self.stringify = True
            except ValueError:
                self.stringify = False
        else:
            self.stringify = False

        result = value
        mapping = self._find_map_for_dps(value)
        if mapping:
            scale = mapping.get("scale", 1)
            if not isinstance(scale, (int, float)):
                scale = 1
            redirect = mapping.get("value_redirect")
            replaced = "value" in mapping
            result = mapping.get("value", result)
            cond = self._active_condition(mapping, device)
            if cond:
                if cond.get("invalid", False):
                    return None
                replaced = replaced or "value" in cond
                result = cond.get("value", result)
                scale = cond.get("scale", scale)
                redirect = cond.get("value_redirect", redirect)

                for m in cond.get("mapping", {}):
                    if str(m.get("dps_val")) == str(result):
                        replaced = "value" in m
                        result = m.get("value", result)

            if redirect:
                _LOGGER.debug(f"Redirecting {self.name} to {redirect}")
                r_dps = self._entity.find_dps(redirect)
                return r_dps.get_value(device)

            if scale != 1 and isinstance(result, (int, float)):
                result = result / scale
                replaced = True

            if replaced:
                _LOGGER.debug(
                    "%s: Mapped dps %s value from %s to %s",
                    self._entity._device.name,
                    self.id,
                    value,
                    result,
                )

        return result

    def _find_map_for_value(self, value):
        default = None
        for m in self._config.get("mapping", {}):
            if "dps_val" not in m:
                default = m
            if "value" in m and str(m["value"]) == str(value):
                return m
            for c in m.get("conditions", {}):
                if "value" in c and c["value"] == value:
                    return m
        return default

    def _active_condition(self, mapping, device, value=None):
        constraint = mapping.get("constraint")
        conditions = mapping.get("conditions")
        c_match = None
        if constraint and conditions:
            c_dps = self._entity.find_dps(constraint)
            c_val = None if c_dps is None else device.get_property(c_dps.id)
            for cond in conditions:
                if c_val is not None and c_val == cond.get("dps_val"):
                    c_match = cond
                # when changing, another condition may become active
                # return that if it exists over a current condition
                if value is not None and value == cond.get("value"):
                    return cond

        return c_match

    def get_values_to_set(self, device, value):
        """Return the dps values that would be set when setting to value"""
        result = value
        dps_map = {}
        mapping = self._find_map_for_value(value)
        if mapping:
            replaced = False
            scale = mapping.get("scale", 1)
            redirect = mapping.get("value_redirect")
            if not isinstance(scale, (int, float)):
                scale = 1
            step = mapping.get("step")
            if not isinstance(step, (int, float)):
                step = None
            if "dps_val" in mapping:
                result = mapping["dps_val"]
                replaced = True
            # Conditions may have side effect of setting another value.
            cond = self._active_condition(mapping, device, value)
            if cond:
                if cond.get("value") == value:
                    c_dps = self._entity.find_dps(mapping["constraint"])
                    c_val = c_dps._map_from_dps(
                        cond.get("dps_val", device.get_property(c_dps.id)),
                        device,
                    )
                    dps_map.update(c_dps.get_values_to_set(device, c_val))

                # Allow simple conditional mapping overrides
                for m in cond.get("mapping", {}):
                    if m.get("value") == value:
                        result = m.get("dps_val", result)

                scale = cond.get("scale", scale)
                step = cond.get("step", step)
                redirect = cond.get("value_redirect", redirect)

            if redirect:
                _LOGGER.debug(f"Redirecting {self.name} to {redirect}")
                r_dps = self._entity.find_dps(redirect)
                return r_dps.get_values_to_set(device, value)

            if scale != 1 and isinstance(result, (int, float)):
                _LOGGER.debug(f"Scaling {result} by {scale}")
                result = result * scale
                remap = self._find_map_for_value(result)
                if remap and "dps_val" in remap and "dps_val" not in mapping:
                    result = remap["dps_val"]
                replaced = True

            if step and isinstance(result, (int, float)):
                _LOGGER.debug(f"Stepping {result} to {step}")
                result = step * round(float(result) / step)
                remap = self._find_map_for_value(result)
                if remap and "dps_val" in remap and "dps_val" not in mapping:
                    result = remap["dps_val"]
                replaced = True

            if replaced:
                _LOGGER.debug(
                    "%s: Mapped dps %s to %s from %s",
                    self._entity._device.name,
                    self.id,
                    result,
                    value,
                )

        r = self.range(device, scaled=False)
        if r:
            minimum = r["min"]
            maximum = r["max"]
            if result < minimum or result > maximum:
                # Output scaled values in the error message
                r = self.range(device, scaled=True)
                minimum = r["min"]
                maximum = r["max"]
                raise ValueError(
                    f"{self.name} ({value}) must be between {minimum} and {maximum}"
                )

        if self.type is int:
            _LOGGER.debug(f"Rounding {self.name}")
            result = int(round(result))
        elif self.type is bool:
            result = True if result else False
        elif self.type is float:
            result = float(result)
        elif self.type is str:
            result = str(result)

        if self.stringify:
            result = str(result)

        dps_map[self.id] = result
        return dps_map

    def icon_rule(self, device):
        mapping = self._find_map_for_dps(device.get_property(self.id))
        icon = None
        priority = 100
        if mapping:
            icon = mapping.get("icon", icon)
            priority = mapping.get("icon_priority", 10 if icon else 100)
            cond = self._active_condition(mapping, device)
            if cond and cond.get("icon_priority", 10) < priority:
                icon = cond.get("icon", icon)
                priority = cond.get("icon_priority", 10 if icon else 100)

        return {"priority": priority, "icon": icon}


def available_configs():
    """List the available config files."""
    _CONFIG_DIR = dirname(config_dir.__file__)

    for (path, dirs, files) in walk(_CONFIG_DIR):
        for basename in sorted(files):
            if fnmatch(basename, "*.yaml"):
                yield basename


def possible_matches(dps):
    """Return possible matching configs for a given set of dps values."""
    for cfg in available_configs():
        parsed = TuyaDeviceConfig(cfg)
        if parsed.matches(dps):
            yield parsed


def get_config(conf_type):
    """
    Return a config to use with config_type.
    """
    _CONFIG_DIR = dirname(config_dir.__file__)
    fname = conf_type + ".yaml"
    fpath = join(_CONFIG_DIR, fname)
    if exists(fpath):
        return TuyaDeviceConfig(fname)
    else:
        return config_for_legacy_use(conf_type)


def config_for_legacy_use(conf_type):
    """
    Return a config to use with config_type for legacy transition.
    Note: as there are two variants for Kogan Socket, this is not guaranteed
    to be the correct config for the device, so only use it for looking up
    the legacy class during the transition period.
    """
    for cfg in available_configs():
        parsed = TuyaDeviceConfig(cfg)
        if parsed.legacy_type == conf_type:
            return parsed

    return None
