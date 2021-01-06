class ConfigFile:
    def __init__(self, path="config.py"):
        # Guess the selected dir and config filename
        # Should accept:
        # - absolute path (inc. filename)
        # - relative path (inc. filename)
        # - absolute path (exc. filename)
        # - relative path (exc. filename)
        # - shortcouts like ~ . etc
        self.path = path
        self.config = None

    def read_config_file(self,path):
        # Get the absolute path
        abspath = os.path.abspath(path)
        # Is a dir? Then add config.py (default filename)
        if os.path.isdir(abspath):
            abspath += "/config.py"
        # split directory and filename
        directory = os.path.dirname(abspath)
        filename  = os.path.basename(abspath)

        old_syspath = sys.path
        sys.path.append(directory)
        exec("import %s as config" %filename.split(".")[0])
        self.config = config
