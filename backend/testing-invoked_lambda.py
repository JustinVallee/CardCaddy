def lambda_handler(event, context):
    try:
        round_scores_obj = event.get("round_scores_obj")
        date = event.get("date")
        condition = event.get("condition")

        return {
            "statusCode": 200,
            "body": {
                'date': date,
                'condition': condition,
                'round_scores_obj': round_scores_obj
            }
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "statusCode": 500,
            "body": f"An error occurred: {e}"
        }
