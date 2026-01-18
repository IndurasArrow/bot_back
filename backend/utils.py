def df_to_context(df, title: str) -> str:
    rows = df.to_dict(orient="records")
    context = f"{title}:\n"
    for r in rows:
        context += f"{r}\n"
    return context
