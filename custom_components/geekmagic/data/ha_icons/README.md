# Home Assistant Icon Definitions

This directory contains icon definition files downloaded from the
[Home Assistant Core repository](https://github.com/home-assistant/core).

## Source

These JSON files are copied from:
`https://github.com/home-assistant/core/tree/dev/homeassistant/components/{component}/icons.json`

## License

Home Assistant is licensed under the Apache License 2.0.

```
Copyright Home Assistant Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

See: https://github.com/home-assistant/core/blob/dev/LICENSE.md

## Updating

To update these icon definitions, run:

```bash
uv run python scripts/sync_ha_icons.py
```

This will download the latest icon definitions from Home Assistant Core.
