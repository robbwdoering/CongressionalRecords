"""
Robb Doering
robbwdoering@gmail.com

This program fetches the records of individual congress members that are currently
in office. It can be asked about who a certain member is, how their voting history compares
to those of any individual colleague, or their committee memberships.
For publishing on the Amazon Alexa store. 
"""

from __future__ import print_function
from urllib2 import Request, urlopen, URLError
import json


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------


def get_welcome_response():
    session_attributes = {}
    card_title = "Welcome"
    
    speech_output = "Welcome to the Congress Record. " \
                    "Please ask me about a congressman currently in office " \
                    "by saying something like " \
                    "Who is Paul Ryan? " \
                    "or, " \
                    "How is Paul Ryan compared to Nancy Polosi?" \
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = None
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_help_response():
    session_attributes = {}
    card_title = "Help"
    
    speech_output = "I am here to help you keep congresss accountable. " \
                    "Congressional Records knows all about people currently serving in congress, " \
                    "as well as all of their memberships in committees, one of the " \
                    "most important responsiblities of any congress person. " \
                    "Try asking about individuals, how they're compared to others, " \
                    "or their committee memberships. " \
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = None
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for checking up on your government. " \
                    "Stay informed! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

 
def getCongressId(intent, name, currentMembers):
    '''
    This function only works for currently serving members. 
    If only one valid response is found, it returns just the ID.
    If more than are found, it returns a tuple of tuples, each containing an id:name pair. 
    Also always returns reprompt text, which is simply None if no issues were found.
    '''

    validResponses = ()
    reprompt_text = None

    name = name.lower()
    #This checks current members for the name, checking both full names and just first + last.
    #Should be decently fast, on personal clock double checking didn't effect speed over 50ms
    for element in currentMembers:
        first = element['name']['first'].lower()
        last = element['name']['last'].lower()
        full = element['name']['official_full'].lower()
        if 'nickname' in element['name']:
            nickname = element['name']['nickname'].lower()
            booleanMatch = (full == name or first + ' ' + last == name or nickname + ' ' + last == name)
        else:
            booleanMatch = (full == name or first + ' ' + last == name)

        if booleanMatch:
            validResponses += ((element['id']['bioguide'], element['name']['official_full']),)


    if (len(validResponses) == 0):
        with open('past_members.json') as data:
            pastMembers = json.load(data)
            
        for element in pastMembers:
            if (element['name']['first'] + ' ' + element['name']['last']).lower() == name:
                reprompt_text = "No one in modern congress matched that name, but I found a past member. Is that what you were looking for?"
                return element
        
        #if no matchin congressman ever served, it will simply pass an error. 
        reprompt_text = "Sorry, I couldn't recognize the name " + name + ". " \
                        "Please try stating your request again."

    elif (len(validResponses) > 1):
        concatenatedNames = ""
        for element in validResponses:
            (state, party) = getBasicDetails(('state', 'party'), element[0], currentMembers)

            #This simple if block with check if the user has already specified what state and party the legislator belongs to
            if 'state' in intent['slots']:
                if 'state' == intent['slots']['state']:
                    return (cantidate[0], None)

            #Else, this statement when looped creates a meaningful response to clarify.     
            concatenatedNames += "{0}, the {1} from {2}, or ".format(element[1], party, state)

        reprompt_text = "It looks like there's multiple legistlators with the same name. " \
                "Please ask again, specifying either " + concatenatedNames[0:-5] + "."
    else:
        validResponses = validResponses[0][0]


    return (validResponses, reprompt_text)

def getBasicDetails(desiredResults, ID, currentMembers):
    '''
    OPTIONS: name, elected, state, party, house
    can change order of input, but output is ALWAYS in that order
    (congressmanName, electedDate, state, party, house) = 
    getBasicDetails(('name', 'elected', 'state', 'party', 'house'), ID, currentMembers)
    '''
    
    results = ()
    profile = ""
    
    for element in currentMembers:
        if element['id']['bioguide'] == ID:
            profile = element
            break
        

    if 'name' in desiredResults:
        results += (profile['name']['first'] + ' ' + profile['name']['last'],)

    #finds the year when they were first elected to the house
    if 'elected' in desiredResults:
        results += (profile['terms'][0]['start'][0:4],)

    #gives the two digit state code. 
    if 'state' in desiredResults:
        results += (profile['terms'][-1]['state'],)

    #finds the party the legislator was most recently part of
    if 'party' in desiredResults:
        results += (profile['terms'][-1]['party'],)

    #finds the house of congress they have served in. Either 'house', 'senate', or 'both houses of congress'
    if 'house' in desiredResults:
        houseCount = [0, 0]
        for term in profile['terms']:
            if term['type'] == 'rep':
                houseCount[0] += 1
            elif term['type'] == 'sen':
                houseCount[1] += 1
        houseCount = (str(houseCount[0]), str(houseCount[1]))
        results += (houseCount,)

    return results

    
def general_record_check(intent, session, currentMembers):
    '''
    This function handles the intent asking about the basic details of some specific congressman.
    Returns a response properly formatted to work with Alexa. 
    '''
    card_title = "General Record Info"
    session_attributes = {}
    should_end_session = False
    speech_output = "I'm sorry, your congressman couldn't be found in my records."
    
    congressmanName = (intent['slots']['congressman']['value'])
    (ID, reprompt_text) = getCongressId(intent, congressmanName, currentMembers)


    #This checks whether an individual congressman was found before continuing
    if reprompt_text == None:
        (congressmanName, electedDate, state, party, house) =  getBasicDetails(('name', 'elected',
            'state', 'party', 'house'), ID, currentMembers)
        speech_output = "{0} is a {1} hailing from {2}, first elected to congress in {3}. " \
                "They have served {4} terms in the house, and {5} terms in the senate.".format(congressmanName, party, state, electedDate, house[0], house[1])
                
    elif reprompt_text[0:10] == "No one in ":
        (congressmanName, electedDate, state, party) =  (ID['name']['first'] + ' ' + ID['name']['last'],
            ID['terms'][0]['start'][0:4], ID['terms'][-1]['state'], ID['terms'][-1]['party'])
            
        house = [0, 0]
        for term in ID['terms']:
            if term['type'] == 'rep':
                house[0] += 1
            elif term['type'] == 'sen':
                house[1] += 1
        house = (str(house[0]), str(house[1]))
        
        speech_output = "{0} is a {1} hailing from {2}, first elected to congress in {3}. " \
                "They have served {4} terms in the house, and {5} terms in the senate.".format(congressmanName, party, state, electedDate, house[0], house[1])

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def individual_committee_check(intent, session, currentMembers):
    '''
    This function handles the intent asking about the committee memberships of a congressman.
    Returns a response properly formatted to work with Alexa. 
    '''
    card_title = "Individual Committee Info"
    session_attributes = {}
    should_end_session = False
    speech_output = ""

    
    congressmanName = (intent['slots']['congressman']['value'])
    (ID, reprompt_text) = getCongressId(intent, congressmanName, currentMembers)

    if reprompt_text == None:
        committeeAssignments = {}
        with open('committee_members.json') as data:
            jsonData = json.load(data)

        for committee in jsonData:
            for member in jsonData[committee]:
                if member['bioguide'] == ID:
                    committeeAssignments[committee] = member['rank']

        


        speech_output = congressmanName + ' holds the chair of rank '
        count = 0
        for assignment in committeeAssignments:
            if count == (len(committeeAssignments) - 1) and len(committeeAssignments) != 1:
                speech_output += 'and {0} in the {1}.'.format(committeeAssignments[assignment], assignment) 
            else:
                speech_output += '{0} in the {1}, '.format(committeeAssignments[assignment], assignment)
            count = count + 1



    
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def record_compare(intent, session, currentMembers):
    '''
    This function handles the intent asking about how two congresspeople compare.
    Returns a response properly formatted to work with Alexa. 
    '''
    card_title = "Comparison"
    session_attributes = {}
    should_end_session = False
    speech_output = ""

    congressmanName1 = (intent['slots']['congressmanOne']['value'])
    congressmanName2 = (intent['slots']['congressmanTwo']['value'])

    (ID1, reprompt_text1) = getCongressId(intent, congressmanName1, currentMembers)
    (ID2, reprompt_text2) = getCongressId(intent, congressmanName2, currentMembers)


    if reprompt_text1 == None and reprompt_text2 == None:
        for element in currentMembers:
            if element['id']['bioguide'] == ID1:
                if element['terms'][-1]['type'] == 'sen':
                    house = 'senate'
                else:
                    house = 'house'
                break
        
        totalVotesShared = 0
        votesDisagree = 0
        #loops through the three most recent congresses. 
        for num in range(113, 115):
            #First half of this code checks whether both congressman served in the same chamber. 

            firstFound = False
            secondFound = False

            response = Request("https://api.propublica.org/congress/v1/{0}/{1}/members.json".format(num, house), 
                headers={"X-API-Key" : "DIl7ejWZz5ajxyzYyOjDN89YLp1xekEb1mjWkjq1"})
            response = urlopen(response)
            membership = json.load(response)
            for member in membership['results'][0]['members']:
                if ID1 == member['id']:
                    firstFound = True
                if ID2 == member['id']:
                    secondFound = True


            #And the second half gets the desired info only if they did. 
            if firstFound and secondFound:
                response = Request("https://api.propublica.org/congress/v1/members/{0}/votes/{1}/{2}/{3}.json".format(ID1, ID2, num, house), 
                    headers={"X-API-Key" : "DIl7ejWZz5ajxyzYyOjDN89YLp1xekEb1mjWkjq1"})
                response = urlopen(response)
                votes = json.load(response)
                totalVotesShared = totalVotesShared + votes['results'][0]['common_votes']
                votesDisagree = votesDisagree + votes['results'][0]['disagree_votes']
        if totalVotesShared == 0:
            speech_output = '{0} and {1} have never voted on the same issue, most likely because they weren\'t in office at the same time'.format(congressmanName1, congressmanName2)
        else:
            speech_output = '{0} and {1} have voted on the same issue {2} times, and agreed about {3} percent of the time.'.format(
                congressmanName1, congressmanName2, totalVotesShared, (totalVotesShared / (totalVotesShared - votesDisagree)))

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text1, should_end_session))

    


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    with open('current_members.json') as data:
        currentMembers = json.load(data)


    # Dispatch to your skill's intent handlers
    if intent_name == "generalRecordCheck":
        return general_record_check(intent, session, currentMembers)
    elif intent_name == "indivCommitteeCheck":
        return individual_committee_check(intent, session, currentMembers)
    elif intent_name == "recordCompare":
        return record_compare(intent, session, currentMembers)
    elif intent_name == "AMAZON.HelpIntent":
        return get_help_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    #if (event['session']['application']['applicationId'] !=
     #        "amzn1.ask.skill.ef0a117c-a47d-4ca5-97d3-570f9383c01a"):
     #    raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])






