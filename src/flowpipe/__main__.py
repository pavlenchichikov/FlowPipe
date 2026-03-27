"""CLI entry point for FlowPipe."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="flowpipe",
        description="FlowPipe — Visual ETL pipeline builder",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=8100, help="Port to bind (default: 8100)"
    )
    parser.add_argument(
        "--reload", action="store_true", help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s 0.1.0"
    )

    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn is required. Install with: pip install flowpipe-etl")
        sys.exit(1)

    print(f"  FlowPipe v0.1.0")
    print(f"  Starting at http://{args.host}:{args.port}")
    print()

    uvicorn.run(
        "flowpipe.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
