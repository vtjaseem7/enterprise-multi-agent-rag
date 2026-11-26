from app.ingestion.pipeline import ingest_file


def main() -> None:
    print("Starting ingestion for auth_guide.txt...")
    result = ingest_file(
        file_path="data/raw/auth_guide.txt",
        tenant_id="tenant_acme",
        allowed_roles=["admin", "employee", "customer"],
        allowed_groups=["support", "engineering"],
        category="technical_docs",
    )
    print("Ingestion complete!")
    print(result)


if __name__ == "__main__":
    main()