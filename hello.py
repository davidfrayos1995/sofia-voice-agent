import modal

app = modal.App("test-suspension")

@app.function()
def hello():
    return "Modal está funcionando correctamente"

@app.local_entrypoint()
def main():
    print(hello.remote())
