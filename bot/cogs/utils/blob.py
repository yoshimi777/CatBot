from chatterbot import ChatBot
import logging
from chatterbot.utils import input_function


'''
Train the bot 
'''


# Enable debug level logging
logging.basicConfig(level=logging.DEBUG)

chatbot = ChatBot(
    'Catbot',
    storage_adapter="chatterbot.storage.SQLStorageAdapter",
    filters=["chatterbot.filters.RepetitiveResponseFilter"],
    logic_adapters=[
        # "chatterbot.logic.MathematicalEvaluation",
        # "chatterbot.logic.TimeLogicAdapter",
        {
            'import_path':"chatterbot.logic.BestMatch",
            #'statement_comparison_function': 'chatterbot.comparisons.jaccard_similarity',
            'statement_comparison_function': 'chatterbot.comparisons.levenshtein_distance',
            'sentiment_comparison': 'chatterbot.response_selection.get_first_response'
        },

    ],
    input_adapter="chatterbot.input.TerminalAdapter",
    output_adapter="chatterbot.output.TerminalAdapter",
    database="data.db",
    trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

# Uncomment to train
# def trainbot():
#     chatbot.train('botdata.data')
# trainbot()

def get_feedback():

    text = input_function()

    if 'yes' in text.lower():
        return True
    elif 'no' in text.lower():
        return False
    else:
        print('Please type either "Yes" or "No"')
        return get_feedback()


print('Type something to begin...')

# The following loop will execute each time the user enters input
while True:
    try:
        input_statement = chatbot.input.process_input_statement()
        # conversation_id = chatbot.storage.create_conversation()
        statement, response = chatbot.generate_response(input_statement, conversation_id=None)
        print('Is "{}" an appropriate response to "{}"?'.format(response.text, input_statement))
        if get_feedback():
            chatbot.learn_response(response, input_statement)
        else:
            print('Say what??')
            better = chatbot.input.process_input_statement()
            chatbot.learn_response(better, input_statement)

    # Press ctrl-c or ctrl-d on the keyboard to exit
    except (KeyboardInterrupt, EOFError, SystemExit):
        break
