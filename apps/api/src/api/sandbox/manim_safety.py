"""Static safety guard for LLM-generated Manim code.

`manim_code` is Python executed on our host, so before running it we statically
reject anything that imports outside a small allowlist or uses dangerous
builtins (file/network/process access, dynamic exec). This is the floor — a
locked-down container is the real isolation (see the spec) — but it stops the
obvious foot-guns from a hallucinated import.
"""

import ast
import logging

logger = logging.getLogger("api.manim.safety")

_ALLOWED_IMPORTS = {"manim", "numpy", "np", "math", "random"}
_BANNED_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "input",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
}
_BANNED_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "requests", "httpx", "urllib"}


def is_safe_manim(code: str) -> bool:
    """True if `code` parses and uses only allowlisted imports/builtins."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        logger.warning("manim code rejected: syntax error")
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _BANNED_MODULES or root not in _ALLOWED_IMPORTS:
                    logger.warning("manim code rejected: import %r", alias.name)
                    return False
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BANNED_MODULES or root not in _ALLOWED_IMPORTS:
                logger.warning("manim code rejected: from-import %r", node.module)
                return False
        elif isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            logger.warning("manim code rejected: banned name %r", node.id)
            return False
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            # block dunder attribute access (e.g. __globals__, __builtins__)
            logger.warning("manim code rejected: dunder attribute %r", node.attr)
            return False
    return True
