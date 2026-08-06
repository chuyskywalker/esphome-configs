A source for my ESPHome configs

```bash
docker pull ghcr.io/esphome/esphome
docker run --name esphome --rm -p 6052:6052 -e ESPHOME_DASHBOARD_USE_PING=true \
       -v "${PWD}"/device-yamls:/config \
       -v "${PWD}"/solark:/solark \
       -v "${PWD}"/n60:/n60 \
       -it ghcr.io/esphome/esphome
```

In another terminal, for python/etc operations:

```bash
docker exec -ti esphome bash
```

Generate key/pass like this:
```bash
openssl rand -base64 32
openssl rand -hex 16
```
