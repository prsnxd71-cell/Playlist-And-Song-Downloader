"""
PL Downloader - Main Application Entrypoint.
Launches the Desktop GUI or delegates to CLI if arguments are supplied.
"""
import sys

def main():
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        # Convenience: Allow passing URL directly via CLI
        from test_cli import main as cli_main
        cli_main()
    else:
        from ui.main_window import run_app
        run_app()

if __name__ == "__main__":
    main()
