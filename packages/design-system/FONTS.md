# Fonts
The requested Google Fonts Host Grotesk and Instrument Sans TTFs were inspected with fontTools. Both lack Vietnamese O/U horn and many precomposed tone characters. They are not used for mixed Vietnamese text.

Be Vietnam Pro replaces BOTH heading and body fonts explicitly. Regular (400), SemiBold (600), Bold (700) are self-hosted, from https://github.com/google/fonts/tree/main/ofl/bevietnampro . OFL license is included. No third-party font request at runtime. The full Vietnamese alphabet and tone combinations are checked by the preparation report.

LiquidGlass1/LiquidGlass2 are visual references only. Their code and embedded refraction image are not redistributed. Our CSS surface/radio controls are an original, simple implementation with solid/blur fallback and no refraction dependency.
