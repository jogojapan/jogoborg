# Python Virtual Environment Setup Guide

## Why Use a Virtual Environment?

A Python virtual environment isolates your project's dependencies from your system Python installation. This is a best practice for several reasons:

- ✅ **Dependency Isolation**: Jogoborg's dependencies don't conflict with other projects
- ✅ **Clean System**: Keeps your system Python clean and unmodified
- ✅ **Reproducibility**: Same environment across different machines
- ✅ **Easy Cleanup**: Delete the venv directory to remove all dependencies
- ✅ **Multiple Projects**: Run different Python projects with different dependency versions

## Quick Setup

### 1. Create Virtual Environment

From the **project root** (not inside `local_test/`):

```bash
python3 -m venv venv
```

This creates a `venv/` directory with an isolated Python environment.

### 2. Activate Virtual Environment

**On Linux/macOS:**
```bash
source venv/bin/activate
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**On Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

### 3. Verify Activation

You should see `(venv)` in your prompt:

```bash
(venv) user@machine:~/jogoborg$
```

### 4. Proceed with Setup

Now you can safely run the local testing setup:

```bash
cd local_test
./setup.sh
./run_local.sh
```

## Deactivating Virtual Environment

When you're done developing, deactivate the virtual environment:

```bash
deactivate
```

The prompt will return to normal (no `(venv)` prefix).

## Reactivating Virtual Environment

To work on the project again, simply activate the virtual environment:

```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

## Troubleshooting

### "command not found: python3"

Make sure Python 3 is installed:

```bash
python3 --version
```

If not installed, install Python 3.7+ from https://www.python.org/

### "Permission denied" on Linux/macOS

Make sure the activation script is executable:

```bash
chmod +x venv/bin/activate
```

### Virtual environment not activating

Try using the full path:

```bash
source /full/path/to/venv/bin/activate
```

### "ModuleNotFoundError" after activating venv

Make sure you're in the activated virtual environment:

```bash
which python  # Should show path inside venv/
```

If not, activate again:

```bash
source venv/bin/activate
```

## Cleaning Up

To remove the virtual environment and all installed packages:

```bash
rm -rf venv
```

This doesn't affect your project code, only the isolated Python environment.

## Best Practices

1. **Always activate before working**: Make sure `(venv)` is in your prompt
2. **Don't commit venv**: Add `venv/` to `.gitignore` (already done in this project)
3. **Recreate if needed**: You can always delete and recreate the venv
4. **Use for all Python work**: Activate venv for any Python development on this project

## Integration with Local Testing

The local testing setup (`setup.sh`) will:

1. Check if you're in a virtual environment
2. Warn you if you're not (but allow you to continue)
3. Install required Python packages in the virtual environment

**Recommended workflow:**

```bash
# 1. Create and activate venv (one-time)
python3 -m venv venv
source venv/bin/activate

# 2. Setup local testing (one-time)
cd local_test
./setup.sh

# 3. Start services
./run_local.sh

# 4. Work on the project...

# 5. Stop services
./stop_local.sh

# 6. Deactivate when done
deactivate
```

## Additional Resources

- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [Virtual Environments Guide](https://docs.python.org/3/tutorial/venv.html)
- [Best Practices for Python Development](https://docs.python-guide.org/dev/virtualenvs/)

## Summary

Using a Python virtual environment is a best practice that:
- Isolates dependencies
- Prevents conflicts
- Makes your setup reproducible
- Keeps your system clean

**Recommended**: Always use a virtual environment for this project.

