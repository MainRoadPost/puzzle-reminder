# Puzzle reminder

## Description

This is an example of how to check reports filled in by users.
The program requests information from Puzzle regarding reports submitted by the user and displays a pop-up notification if any days have not been completed.
Authorisation is not needed for this request, only the username (login) from an .env file.

```shell
uv run --script ./reminder.py
```

## Changing the generated client

The GraphQL client for Puzzle is generated into the `puzzle` module by `ariadne-codegen`. Do not edit the generated client code by hand.

To update the client after schema or query changes:

1. Make sure `schema.graphql` contains an up-to-date schema.
2. Update `queries.graphql` with the required queries/mutations.
3. Regenerate the client:

   ```bash
   uv run ariadne-codegen
   ```

**Note:** Running `ariadne-codegen` is required before the first run and after any changes to schema or query files.

## Updating the schema

To update the schema you need the `cynic-cli` tool (requires [Rust](https://www.rust-lang.org/tools/install) to be installed):

```shell
cargo install --git https://github.com/obmarg/cynic.git cynic-cli
```

After installing `cynic-cli`, run `./get-schema.sh > schema.graphql` in the repository root to authenticate against the Puzzle server and download the current GraphQL schema.

The script expects the following environment variables to be set in `.env`:
- `PUZZLE_API` — GraphQL endpoint URL of the Puzzle server.
- `PUZZLE_USER_DOMAIN` — studio domain (leave blank if not used).
- `PUZZLE_USERNAME` — username to authenticate with.
- `PUZZLE_PASSWORD` — password for the user.

Optionally, set `LOG_LEVEL` (e.g., `LOG_LEVEL=INFO`) to control logging verbosity.

See `example.env` for an example `.env` file.
