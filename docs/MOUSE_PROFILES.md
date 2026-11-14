# Mouse identification and wheel data

Checked 2026-11-14. This is a partial-data catalog, not an accuracy certification.
No complete outer-wheel-diameter + Raw-Input-increments profile was established
from the manufacturer sources below. Unknown diameters are never auto-filled as
verified measurements. Product dimensions describe the mouse body, not its wheel.

| Exact model | Published wheel information | Source |
|---|---|---|
| Razer DeathAdder V4 Pro | 24 steps; diameter unavailable | [Razer support](https://mysupport.razer.com/app/answers/detail/a_id/19852) |
| Razer Viper V4 Pro | 24 steps; diameter unavailable | [Razer support](https://mysupport.razer.com/app/answers/detail/a_id/20775) |
| Razer Naga V3 Pro | Selectable 24 / 48 step modes; diameter unavailable | [Razer support](https://mysupport.razer.com/app/answers/detail/a_id/21025) |
| Razer Naga V2 Pro | Configurable 8–96 steps; diameter unavailable | [Razer wheel technology](https://www.razer.com/technology/razer-scroll-wheels) |
| Razer Basilisk V4 Pro | Selectable 24 / 48 step modes; diameter unavailable | [Razer support](https://mysupport.razer.com/app/answers/detail/a_id/21064) |

Tactile steps are not guaranteed to correspond one-for-one to conventional Windows
scroll increments on every firmware/mode combination. The one-turn helper records
the actual Raw Input deltas for the current mode. Detected product strings are
treated as device-reported names, not authenticated model identities. Receiver
or generic-device strings cannot establish the paired mouse model. VID/PID identify
vendor/product endpoints but do not establish physical wheel geometry.

Contribute a complete profile only with an exact model/revision, wheel mode, outer
diameter source, reported increments per revolution, and repeatable physical checks.
Do not use encoder shaft height, mouse-body dimensions, or a similar model as wheel
diameter. Keep unsupported fields unknown and attach source URLs to each fact.
