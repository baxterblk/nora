def register():
    def run(model, call_fn):
        prompt = "Introduce yourself like a friendly CLI agent."
        call_fn([{"role": "user", "content": prompt}], model=model, stream=True)

    return {
        "name": "greeter",
        "description": "A simple starter agent",
        "run": run
    }
