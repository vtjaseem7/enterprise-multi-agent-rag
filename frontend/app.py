import requests
import streamlit as st
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Enterprise Multi-Agent RAG", layout="wide")
st.title("Enterprise Multi-Agent RAG Assistant")


with st.sidebar:
    st.header("Session Settings")
    role = st.selectbox("Select Role (Dev Auth)", ["customer", "employee", "admin"])
    tenant_id = st.text_input("Tenant ID", value="tenant_acme")

    if (
        "token" not in st.session_state
        or st.session_state.get("role") != role
        or st.session_state.get("tenant_id") != tenant_id
    ):
        try:
            resp = requests.post(
                f"{API_BASE_URL}/api/v1/auth/dev-token",
                json={"user_id": f"{role}_1", "tenant_id": tenant_id, "role": role},
                timeout=10,
            )
            resp.raise_for_status()
            st.session_state.token = resp.json()["access_token"]
            st.session_state.role = role
            st.session_state.tenant_id = tenant_id
            st.session_state.messages = []  # Reset chat when switching roles
            st.success(f"Authenticated as {role}")
        except requests.RequestException as exc:
            st.error(f"Could not connect to FastAPI: {exc}")

    if role == "admin":
        st.divider()
        st.subheader("Admin: Upload Document")
        uploaded_file = st.file_uploader("Upload .txt, .md, or .pdf", type=["txt", "md", "pdf"])
        category = st.text_input("Category", value="general")
        allowed_roles = st.text_input("Allowed Roles (comma-separated)", value="admin,employee")

        if st.button("Upload & Index") and uploaded_file is not None:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            data = {"category": category, "allowed_roles": allowed_roles}
            with st.spinner("Indexing document into Qdrant..."):
                res = requests.post(
                    f"{API_BASE_URL}/api/v1/documents/upload",
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=60,
                )
            if res.status_code == 200:
                info = res.json()
                st.success(f"Indexed {info['source']} ({info['chunks_indexed']} chunks)")
            else:
                st.error(f"Upload failed ({res.status_code}): {res.text}")


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("meta"):
            st.caption(msg["meta"])

if prompt := st.chat_input("Ask a question about company docs..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            res = requests.post(
                f"{API_BASE_URL}/api/v1/chat",
                headers=headers,
                json={"query": prompt},
                timeout=60,
            )
        if res.status_code == 200:
            data = res.json()
            answer = data["answer"]
            citations = ", ".join(data["citations"]) if data["citations"] else "None"
            cache_label = "HIT (0 LLM tokens)" if data["cached"] else "MISS"
            meta = f"Path: {data['route']} | Cache: {cache_label} | Citations: {citations}"

            st.markdown(answer)
            st.caption(meta)
            st.session_state.messages.append({"role": "assistant", "content": answer, "meta": meta})
        else:
            st.error(f"API Error ({res.status_code}): {res.text}")