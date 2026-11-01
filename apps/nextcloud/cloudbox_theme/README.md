# CloudBox theme for Nextcloud 35
Uses the public IBootstrap/BeforeTemplateRenderedEvent/Util::addStyle APIs. CSS maps documented semantic variables and existing application containers. No core file or compiled bundle patch, JavaScript injection, API interception or replacement Files renderer.
Disable with `php occ app:disable cloudbox_theme`. All upstream themes and accessibility controls remain native. High-contrast themes do not receive our palette; the dyslexia font is not replaced. User background choices are not suppressed. Upgrades beyond Nextcloud 35 require review; info.xml deliberately gates compatibility to 35.
Fonts are self-hosted Be Vietnam Pro (OFL), generated CSS shares canonical design-system tokens. Files/theme previews are references, not a separate data system.
