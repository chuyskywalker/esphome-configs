A source for my ESPHome configs

```bash
docker pull ghcr.io/esphome/esphome
docker run --rm -p 6052:6052 -e ESPHOME_DASHBOARD_USE_PING=true -v "${PWD}":/config -it ghcr.io/esphome/esphome
```
