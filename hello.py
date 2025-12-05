def greet(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    def greet_kr(name: str = "") -> str:
        if not name:
            name = "친구"
        return f"안녕하세요, {name}!"

    print(greet_kr())
