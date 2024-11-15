import logging
import shutil

log = logging.getLogger("mkdocs")


def on_post_build(*args, **kwargs):
    log.info("Adding additional files")
    shutil.copytree("own_your_data", "site/own_your_data", dirs_exist_ok=True)
    shutil.copy("playground.html", "site/playground.html")
    shutil.copy("CNAME", "site/CNAME")
