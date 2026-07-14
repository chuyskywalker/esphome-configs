A source for my ESPHome configs

```bash
docker pull ghcr.io/esphome/esphome
docker run --rm -p 6052:6052 -e ESPHOME_DASHBOARD_USE_PING=true -v "${PWD}"/device-yamls:/config -it ghcr.io/esphome/esphome
```

Generate key/pass like this:
```bash
openssl rand -base64 32
openssl rand -hex 16
```
