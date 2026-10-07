IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    ".tox",
    "target",
    "vendor",
}

CODE_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java",
    ".rb", ".rs", ".c", ".cpp", ".cs",
}

EXT_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
}

TEST_PATH_HINTS = ("test", "tests", "spec", "__tests__")
CONFIG_FILENAMES = {
    "pyproject.toml", "requirements.txt", "setup.py", "package.json",
    "Dockerfile", "docker-compose.yml", ".env", "tsconfig.json",
    "pytest.ini", "jest.config.js",
}
DOC_EXTS = {".md", ".rst", ".txt"}

MAX_RETRY_ATTEMPTS = 3
EMBEDDING_DIM = 512

# Above this many lines, whole-file rewrite stops being reliable (context
# window limits on a local model, falling accuracy on huge rewrites) — the
# code generator switches to editing just the relevant chunk instead.
LARGE_FILE_LINE_THRESHOLD = 300
