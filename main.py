from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Layer 1: defaults (lowest precedence) ----
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# ---- Layer 2: config.development.yaml ----
YAML_TEXT = """
port: 8413
debug: true
api_key: key-yb5h0fp34x
"""

# ---- Layer 3: .env file ----
DOTENV_TEXT = """
NUM_WORKERS=8
APP_DEBUG=true
"""

# ---- Layer 4: OS env vars (APP_* prefix) ----
OS_ENV = {
    "APP_PORT": "8903",
    "APP_WORKERS": "8",
    "APP_DEBUG": "false",
    "APP_LOG_LEVEL": "error",
    "APP_API_KEY": "key-9hubayz9rf",
}

ALIASES = {"num_workers": "workers"}
INT_KEYS = {"port", "workers"}
TRUTHY = {"true", "1", "yes", "on"}


def parse_kv(text, sep):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or sep not in line:
            continue
        k, v = line.split(sep, 1)
        out[k.strip()] = v.strip().strip("'\"")
    return out


def norm_key(k):
    k = k.strip().lower()
    if k.startswith("app_"):
        k = k[4:]
    return ALIASES.get(k, k)


def coerce(key, value):
    if key in INT_KEYS:
        return int(str(value).strip())
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in TRUTHY
    return str(value)


def merge_layer(base, layer):
    for k, v in layer.items():
        nk = norm_key(k)
        base[nk] = coerce(nk, v)


def effective(cli_sets):
    cfg = {}
    merge_layer(cfg, DEFAULTS)
    merge_layer(cfg, parse_kv(YAML_TEXT, ":"))
    merge_layer(cfg, parse_kv(DOTENV_TEXT, "="))
    merge_layer(
        cfg, {k: v for k, v in OS_ENV.items() if k.upper().startswith("APP_")}
    )
    for item in cli_sets:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        nk = norm_key(k)
        try:
            cfg[nk] = coerce(nk, v)
        except ValueError:
            pass
    cfg["api_key"] = "****"
    return cfg


@app.get("/effective-config")
def effective_config(request: Request):
    return effective(request.query_params.getlist("set"))


@app.get("/")
def root():
    return {"status": "ok", "endpoint": "/effective-config"}
