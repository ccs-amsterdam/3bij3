# from routes.py, but never used:


@app.context_processor
def user_agent():
    user_string = request.headers.get('User-Agent')
    try:
        user_agent = parse(user_string)
        if user_agent.is_mobile == True:
            device = "mobile"
        elif user_agent.is_tablet == True:
            device = "tablet"
        else:
            device = "pc"
    except:
        user_agent = " "
        device = "pc"
    return dict(device = device)

