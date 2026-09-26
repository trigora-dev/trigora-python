from trigora import effect, program, wait_for_event


@program
async def approval():
    result = await effect("generate", lambda: 42)
    review = await wait_for_event("approved")
    return {"result": result, "review": review}
