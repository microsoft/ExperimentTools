#
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
#
# scanner.py: simple scanner for cmdline parsing
from xtlib import errors

class Scanner():
    def __init__(self, text):
        self.text = text
        self.len = len(text)
        self.index = 0
        self.token_type = None
        self.token = None
        self.prev_index = 0
        #console.print("Scanner created, text=", text)

    def scan(self, allow_extended_ids=True):
        self.prev_index = self.index
        
        text = self.text

        # skip spaces
        while self.index < self.len:
            if text[self.index] == ' ':
                self.index += 1
            else:
                break

        if self.index >= self.len:
            self.token_type =  "eol"
            self.token = None
        else:
            ch = text[self.index]
            start = self.index
            self.index += 1

            if self.index < self.len:
                ch_next = text[self.index]
            else:
                ch_next = None

            if allow_extended_ids and ch.lower() in '~/_abcdefghijklmnopqrstuvwxyz*?$-' or (ch == "." and ch_next in [".", "/", "\\"]):
                # scan an ID or FILENAME or a WILDCARD or box-addr
                while self.index < self.len and text[self.index].lower() in '/@._-abcdefghijklmnopqrstuvwxyz0123456789?*:/\\':
                    self.index += 1
                self.token_type = "id"
                self.token = text[start:self.index]
            elif not allow_extended_ids and ch.lower() in '_abcdefghijklmnopqrstuvwxyz': 
                # scan a simple ID
                while self.index < self.len and text[self.index].lower() in '_abcdefghijklmnopqrstuvwxyz0123456789.-':
                    self.index += 1
                self.token_type = "id"
                self.token = text[start:self.index]
            elif ch in '.0123456789':
                # scan a NUMBER
                while self.index < self.len and text[self.index] in '.0123456789':
                    self.index += 1
                # allow for tags that start with a number but contain letters, and "_"
                ch = text[self.index] if self.index < self.len else None

                if ch and ch.isalpha() and not "." in  text[start:self.index-1]:
                    while self.index < self.len and text[self.index].lower() in '_abcdefghijklmnopqrstuvwxyz0123456789.-':
                        self.index += 1                    
                    self.token_type = "id"
                    self.token = text[start:self.index]
                else:
                    self.token_type = "number"
                    self.token = text[start:self.index]
            elif ch == '"' or ch == "'":
                # scan a STRING
                quote = ch
                last_ch = ""
                while self.index < self.len:
                    if text[self.index] == quote and last_ch != "\\":
                        break
                    last_ch = text[self.index]
                    self.index += 1

                if text[self.index] != quote:
                    errors.raise_error("Unterminated string at offset=" + str(start) + " in cmd: " + text)

                self.token_type = "string"
                self.index += 1        # skip over the ending quote
                self.token = text[start+1:self.index-1]
                # un-embed contained quotes
                self.token = self.token.replace("\\" + quote, quote)
            else:
                # scan a special char
                self.token_type = "special"
                self.token = ch
                if self.index < self.len:
                    ch2 = ch + self.text[self.index]
                    #console.print("ch2=", ch2)
                    if ch2 in ["--", "<=", ">=", "!=", "<>", "=="]:
                        self.index += 1
                        self.token = ch2

        #console.print("scanner.scan returning=", self.token, ", type=", self.token_type)
        return self.token

    def save_state(self):
        state = Scanner(self.text)
        state.len = self.len
        state.index = self.index
        state.token_type = self.token_type
        state.token = self.token
        return state

    def restore_state(self, state):
        self.text = state.text
        self.len = state.len
        self.index = state.index
        self.token_type = state.token_type
        self.token = state.token

    def peek(self):
        # peek ahead 1 token
        state = self.save_state()
        tok = self.scan()
        state = self.restore_state(state)
        return tok

    def get_rest_of_text(self, include_current_token=False):
        if include_current_token:
            text = self.text[self.prev_index:]
        else:
            text = self.text[self.index:]

        # show input all processed
        self.token = text
        self.index = len(self.text)
        self.token_type = "text"

        self.text = text
        self.len = len(text)

        return text
                