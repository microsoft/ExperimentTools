#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# feedbackParts.py: builds up a single line of step-by-step progress (used for xt run cmd)
import sys
from ..console import console

class FeedbackParts():
    def __init__(self):
        self.reset_feedback()

    def reset_feedback(self):
        self.in_feedback = False
        self.feedback_enabled = True
        self.last_msg_len = 0
        self.last_msg_id = None

    def stop_feedback(self):
        if self.in_feedback:
            console.print()
            self.in_feedback = False
        self.feedback_enabled = False

    def feedback(self, msg, is_first=False, is_final=False, add_seperator=True, id=None):
        post = "" if is_final or not add_seperator else ", "
        end = "\n" if is_final else ""

        if not self.feedback_enabled:
            end = "\n"

        # need to erase last msg?
        if id and id == self.last_msg_id:
            console.print("\b" * self.last_msg_len, end="")

        # console.print the msg PART
        console.print(msg + post, end=end)
        sys.stdout.flush()

        self.in_feedback = (end == "")
        self.last_msg_id = id
        self.last_msg_len = len(msg + post)

# make it easy to access a single global instance
feedback = FeedbackParts()


 