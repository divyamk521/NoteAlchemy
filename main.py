from src.utils.retry import groq_retry


counter = 0


@groq_retry
def fake_api_call():
    global counter

    counter += 1

    print(f"Attempt {counter}")

    if counter < 3:
        raise Exception("Temporary API failure")

    return "Success!"


result = fake_api_call()

print(result)