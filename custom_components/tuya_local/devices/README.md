# Device Configuration Files

This directory contains device configuration files, describing the workings
of supported devices. The files are in YAML format, and describe the mapping
of Tuya DPS (Data Point Setting) to HomeAssistant attributes.

Each Tuya device may correspond to one primary entity and any number of
secondary entities in Home Assistant.

## The Top Level

The top level of the device configuration defines the following:

### `name`

The device should be named descriptively with a name the user would recognize,
the brand and model of the device is a good choice.  If a whole family of
devices is supported, a generalization of the model type can be used.
The name should also indicate to the user what type of device it is.

### `legacy_type`

// Optional, deprecated. //

The `legacy_type` is a transitional link back to an old name the device
was known by.  It is used in the migration process to migrate old
configs to the latest config which uses the config filename as the identifier
for the device.  New devices should not define this.

### `products`

// Optional, for future use. //

A list of products that this config applies to.  Each product in the list must
have an `id` specified, which corresponds to the productId or productKey
(depending on where you are getting it from) in Tuya info.  This is available
from the Tuya developer web portal listing for your device, or when using
UDP discovery (via tinytuya).  In future it is intended that UDP discovery
will be used to more precisely match devices to configs, so it is recommended
to report these if you can find them when requesting a new device.  Each
listing can also have an optional `name`, which is intended to override the
top level `name` when full support for this field is added.
Probably other info will be added in future to provide better reporting of
device manufacturer and model etc.

### `primary_entity`

This contains the configuration for one Home Assistant entity which is
considered the main entity for the device. For example, if the device is
a heater, this would be a climate entity.

The configuration for entities is detailed in its own section below.

### `secondary_entities`

//Optional.//

This contains a list of additional Home Assistant entities
providing additional functionality beyond the capabilities of the primary
entity. Examples include lighting control for display panels as a Home
Assistant light entity, child locks as a Home Assistant lock entity,
or additional toggles as Home Assistant switch entities.

The configuration for secondary entities is the same as primary entities,
and is detailed in the section below.

## Entity configuration

### `entity`

The Home Assistant entity type being configured.  Currently supported
types are **climate**, **switch**, **light**, **lock**. Functionality
for these entities is limited to that which has been required for the
devices until now and may need to be extended for new devices.  In
particular, the light and lock entities have only been used for simple
secondary entities, so only basic functionality is implemented.

### `legacy_class`

//Optional, deprecated.//

The `legacy_class` is a transitional link back to the device specific
class that contains the implementation of this device. This allows
a transition for more complex devices that are not yet fully supported
by the generic implementations. It should not be used for new devices.

### `deprecated`

//Optional, deprecated//

This boolean flag is used to mark an entity as deprecated.  This is mainly
for older devices that were implemented when only climate devices were
supported, but are better represented in HA as fan or humidifier devices.
An entity should be moved to `secondary_entities` before being marked as
deprecated, and the preferred device type moved to the `primary_entity`.

### `class`

//Optional.//

For some entity types, a `class` can be set, for example `switch` entities
can have a class of `outlet`.  This may slightly alter the UI behaviour.

### `dps`

This is a list of the definitions for the Tuya DPS associated with
attributes of this entity.  There should be one list entry for each
supported DPS reported by the device. 

The configuration of DPS entries is detailed in its own section below.

### `name`

//Optional.//

The name associated with this entity can be set here. If no name is set,
it will inherit the name at the top level. This is mostly useful for
overriding the name of secondary entities to give more information
about the purpose of the entity, as the generic type with the top level
name may not be sufficient to describe the function.
 
## DPS configuration
 
### `id`
 
Every DPS must have a numeric ID matching the DPS ID in the Tuya protocol.
 
### `type`
 
The type of data returned by the Tuya API. Can be one of the following:
 
 - **string** can contain arbitrary text.
 - **boolean** can contain the values **True** or **False**.
 - **integer** can contain only numbers (the Tuya protocol typically encloses them in quotes as if they are strings, but integers can have range set on them)
 - **bitfield** is a special case of integer, where the bits that make up the value each has individal meaning.

### `name`

The name given to the attribute in Home Assistant. Certain names are used
by the Home Assistant entities for specific purposes.  If a name is not
recognized as a standard attribute by the entitiy implementation, the
attribute will be returned as a readonly custom attribute on the entity.
If you need non-standard attributes to be able to be set, you will need
to use a secondary entity for that.

### `readonly`

//Optional.//

A boolean setting to mark attributes as readonly. If not specified, the
default is `false`.  If set to `true`, the attributes will be reported
to Home Assistant, but no functionality for setting them will be exposed.

### `mapping`

//Optional.//
This can be used to define a list of additional rules that modify the DPS
to Home Assistant attribute mapping to something other than a one to one
copy. 

The rules can range from simple value substitution to complex
relationships involving other attributes. It can also be used to change
the icon of the entity based on the attribute value. Mapping rules are
defined in their own section below.

### `hidden`

//Optional.//
This can be used to define DPS that do not directly expose Home Assistant
attributes.  When set to **true**, no attribute will be sent. A `name` should
still be specified and the attribute can be referenced as a `constraint`
from mapping rules on other attributes to implement complex mappings.

An example of use is a climate device, where the Tuya device keeps separate
temperature settings for different Normal and Eco preset modes.  The Normal
temperature setting is exposed through the standard `temperature`
Home Assistant attribute on the climate device, but the `eco_temperature`
setting on a different DPS is set to hidden. Mapping Rules are used on the
`temperature` attribute to redirect to `eco_temperature` when `preset_mode`
is set to Eco.

### `range`

//Optional.//

For integer attributes that are not readonly, a range can be set with `min`
and `max` values that will limit the values that the user can enter in the
Home Assistant UI.  This can also be set in a `mapping` or `conditions` block.

### `unit`

//Optional. default="C" for temperature dps//

For temperature dps, some devices will use Fahrenhiet.  This needs to be
indicated back to HomeAssistant by defining `unit` as "F".  In future `unit`
will also be used for other sensor types, with a bigger range of possible
values.

## Mapping Rules

Mapping rules can change the behavior of attributes beyond simple
copying of DPS values to attribute values.  Rules can be defined
without a dps_val to apply to all values, or a list of rules that
apply to particular dps values can be defined to change only
particular cases.  Rules can even depend on the values of other
elements.

### `dps_val`

//Optional, if not provided, the rule is a default that will apply to all
values not covered by their own dps_val rule.//
`dps_val` defines the DPS value that each
rule in the list applies to. This can be used to map specific values from the
Tuya protocol into attribute values that have specific meaning in Home
Assistant.  For example, climate entities in Home Assistant define modes
"off", "heat", "cool", "heat_cool", "auto" and "dry". But in the Tuya protocol,
a simple heater just has a boolean off/on switch.  It can also be used to
change the icon when a specific mode is operational.  For example if
a heater device has a fan-only mode, you could change the icon to "mdi:fan"
instead of "mdi:radiator" when in that mode.

### `value`

//Optional.//
This can be used to set the attribute value seen by Home Assistant to something
different than the DPS value from the Tuya protocol.  Normally it will be used
with `dps_val` to map from one value to another. It could also be used at top
level to override all values, but I can't imagine a useful purpose for that.

### `scale`

//Optional, default=1//

This can be used in an `integer` dps mapping to scale the values.  For example
some climate devices represent the temperature as an integer in tenths of
degrees, and require a scale of 10 to convert them to degrees expected by
Home Assistant.  The scale can also be the other way, for a fan with speeds
1, 2 and 3 as DPS values, this can be converted to a percentage with a scale
of 0.03.

### `step`

//Optional, default=1//

This can be used in an `integer` dps mapping to make values jump by a specific
step.  It can also be set in a conditions block so that the steps change only
under certain conditions.  An example is where a value has a range of 0-100, but
only allows settings that are divisible by 10, so a step of 10 would be set.

### `icon`

//Optional.//
This can be used to override the icon.  Most useful with a `dps_val` which
indicates a change from normal operating mode, such as "fan-only",
"defrosting", "tank-full" or some error state.

### `icon_priority`

//Optional. Default 10. Lower numbers mean higher priorities.//
When a number of rules on different attributes define `icon` changes, you
may need to control which have priority over the others.  For example,
if the device is off, probably it is more important to indicate that than
whether it is in fan-only or heat mode.  So in the off/on DPS, you might
give a priority of 1 to the off icon, 3 to the on icon, and in the mode DPS
you could give a priority of 2 to the fan icon, to make it override the
normal on icon, but not the off icon. 
If you don't specify any priorities, the icons will all get the same priority,
so if any overlap exists in the rules, it won't always be predictable which
icon will be displayed.

### `value_redirect`

//Optional.//
When `value_redirect` is set, the value of the attribute and any attempt to
set it will be redirected to the named attribute instead of the current one.

An example of how this can be useful is where a Tuya heater has a dps for the
target temperature in normal mode, and a different dps for the target
temperature is "eco" mode.  Depending on the `preset_mode`, you need to use
one or the other. But Home Assistant just has one `temperature` attribute for
setting target temperature, so the mapping needs to be done before passing to
Home Assistant.

### `invalid`

//Optional. Boolean, default false.//
Invalid set to true allows an attribute to temporarily be set read-only in
some conditions.  Rather than passing requests to set the attribute through
to the Tuya protocol, attempts to set it will throw an error while it meets
the conditions to be `invalid`.  It does not make sense to set this at mapping
level, as it would cause a situation where you can set a value then not be
able to unset it.  Instead, this should be used with conditions, below, to
make the behaviour dependent on another DPS, such as disabling fan speed 
control when the preset is in sleep mode (since sleep mode should force low).


### `constraint`

//Optional. Always paired with `conditions`.//
If a rule depends on an attribute other than the current one, then `constraint`
can be used to specify the element that `conditions` applies to.

### `conditions`

//Optional. Always paired with `constraint.`//
Conditions defines a list of rules that are applied based on the `constraint`
attribute. The contents are the same as Mapping Rules, but `dps_val` applies
to the attribute specified by `constraint`. All others act on the current
attribute as they would in the mapping.  Although conditions are specified
within a mapping, they can also contain a `mapping` of their own to override
that mapping.  These nested mappings are limited to simple `dps_val` to `value`
substitutions, as more complex rules would quickly become too complex to
manage.

