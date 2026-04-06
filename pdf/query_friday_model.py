"""
https://km.sankuai.com/collabpage/1802116743

"""

import os

import streamlit as st
from openai import OpenAI


BASE_URL = "https://aigc.sankuai.com/v1/openai/native"
API_KEY = os.environ["FRIDAY_API_ID"]

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def query_openai(model_name, prompt):
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error querying OpenAI: {str(e)}")
        return None


def main():
    st.title("Query Interface")
    st.write(BASE_URL)

    model_name = st.selectbox(
        "Model",
        [
            "gpt-4o-2024-11-20",
            # "gpt-4o-2024-08-06",
            "anthropic.claude-3.5-sonnet",
            "deepseek-chat",
        ],
    )

    prompt = st.text_area("Enter your prompt:", height=200)

    if st.button("Submit"):
        if not prompt:
            st.error("Please enter a prompt")
            return

        with st.spinner("Generating response..."):
            response = query_openai(model_name, prompt)
            if response:
                st.markdown("### Response:")
                st.write(response)


if __name__ == "__main__":
    main()
