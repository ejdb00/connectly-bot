#!/usr/local/bin/python

import bot.messaging_service as messaging
import sys

def main():
    person_id = int(sys.argv[1])
    messaging.solicit_review_proactively(person_id)
    return 0

if __name__ == '__main__':
    main()