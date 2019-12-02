import json
from typing import Dict, Set, Any
from configparser import ConfigParser
from pathlib import Path


class Config:
    """Base class for loading config files and its parameters"""

    index_links_path: Path = Path("./optimade/server/index_links.json")
    _path: Path = Path("./optimade/server/config.ini")

    def __init__(self, server_cfg: Path = None):
        server = (
            Path(__file__).resolve().parent.parent.parent.joinpath("server.cfg")
            if server_cfg is None
            else server_cfg
        )

        self._create_server_config(server)
        self._load_server_config(server)

        ftype = self._path.suffix[1:]  # Remove initial "."
        self.load(ftype)

    @staticmethod
    def _create_server_config(server_cfg: Path):
        """Create 'server.cfg' in top-package dir from 'server_template.cfg' if it does not exist"""
        if not server_cfg.exists():
            import shutil

            server_cfg_template = (
                Path(__file__)
                .resolve()
                .parent.parent.parent.joinpath("server_template.cfg")
            )
            shutil.copyfile(server_cfg_template, server_cfg)

    def _load_server_config(self, server_cfg: Path):
        """Load cfg-file determining paths to server config files"""
        SECTION = "optimadeconfig"
        INDEX_LINKS_PATH = "INDEX_LINKS"
        SERVER_CONFIG_PATH = "CONFIG"

        server = ConfigParser()
        server.read(server_cfg)

        index_links_path = server.get(
            SECTION, INDEX_LINKS_PATH, fallback=str(self.index_links_path)
        )
        self.index_links_path = server_cfg.parent.joinpath(index_links_path).resolve()

        _path = server.get(SECTION, SERVER_CONFIG_PATH, fallback=str(self._path))
        self._path = server_cfg.parent.joinpath(_path).resolve()

    def _get_load_func(self, format_name) -> Any:
        return getattr(self, f"load_from_{format_name}")

    def load(self, ftype: str = None):
        try:
            f = self._get_load_func(ftype)
        except AttributeError:
            raise NotImplementedError(
                f"load function for config format {ftype} is not implemented"
            )
        else:
            f()


class ServerConfig(Config):
    """ This class stores server config parameters in a way that
    can be easily extended for new config file types.

    """

    use_real_mongo = False
    mongo_database = "optimade"
    links_collection = "links"
    references_collection = "references"
    structures_collection = "structures"

    page_limit = 500
    version = "0.10.0"
    default_db = "test_server"

    provider = {
        "prefix": "_exmpl_",
        "name": "Example provider",
        "description": "Provider used for examples, not to be assigned to a real database",
        "homepage": "http://example.com",
        "index_base_url": "http://example.com/optimade/index",
    }
    provider_fields: Dict[str, Set] = {}

    def load_from_ini(self):
        """ Load from the file "config.ini", if it exists. """

        config = ConfigParser()
        config.read(self._path)

        self.use_real_mongo = config.getboolean(
            "BACKEND", "USE_REAL_MONGO", fallback=self.use_real_mongo
        )
        self.mongo_database = config.get(
            "BACKEND", "MONGO_DATABASE", fallback=self.mongo_database
        )

        self.page_limit = config.getint(
            "IMPLEMENTATION", "PAGE_LIMIT", fallback=self.page_limit
        )
        self.version = config.get("IMPLEMENTATION", "VERSION", fallback=self.version)
        self.default_db = config.get(
            "IMPLEMENTATION", "DEFAULT_DB", fallback=self.default_db
        )

        if "PROVIDER" in config.sections():
            self.provider = dict(config["PROVIDER"])

        self.provider_fields = {}
        for endpoint in {"links", "references", "structures"}:
            self.provider_fields[endpoint] = (
                {field for field, _ in config[endpoint].items() if _ == ""}
                if endpoint in config
                else set()
            )

            # MONGO collections
            setattr(
                self,
                f"{endpoint}_collection",
                config.get(
                    "BACKEND",
                    f"{endpoint.upper()}_COLLECTION",
                    fallback=getattr(self, f"{endpoint}_collection"),
                ),
            )

    def load_from_json(self):
        """ Load from the file "config.json", if it exists. """

        with open(self._path, "r") as f:
            config = json.load(f)

        self.use_real_mongo = bool(config.get("use_real_mongo", self.use_real_mongo))
        self.mongo_database = config.get("mongo_database", self.mongo_database)
        for endpoint in {"links", "references", "structures"}:
            setattr(
                self,
                f"{endpoint}_collection",
                config.get(f"{endpoint}_collection"),
                getattr(self, f"{endpoint}_collection"),
            )

        self.page_limit = int(config.get("page_limit", self.page_limit))
        self.version = config.get("version", self.version)
        self.default_db = config.get("default_db", self.default_db)

        self.provider = config.get("provider", self.provider)
        self.provider_fields = set(config.get("provider_fields", self.provider_fields))


CONFIG = ServerConfig()
