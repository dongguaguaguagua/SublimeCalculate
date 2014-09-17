from functools import cmp_to_key
import math
import random
import re

import sublime
import sublime_plugin


class CalculateCommand(sublime_plugin.TextCommand):
    def __init__(self, *args, **kwargs):
        sublime_plugin.TextCommand.__init__(self, *args, **kwargs)
        self.dict = {}
        for key in dir(random):
            self.dict[key] = getattr(random, key)
        for key in dir(math):
            self.dict[key] = getattr(math, key)

        def average(nums):
            return sum(nums) / len(nums)

        self.dict['avg'] = average
        self.dict['average'] = average

        def password(length=20):
            pwdchrs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            return ''.join(random.choice(pwdchrs) for _ in range(length))

        self.dict['pwd'] = password
        self.dict['password'] = password

    def run(self, edit, **kwargs):
        self.dict['i'] = 0
        for region in self.view.sel():
            try:
                error = self.run_each(edit, region, **kwargs)
            except Exception as exception:
                error = str(exception)

            self.dict['i'] = self.dict['i'] + 1
            if error:
                sublime.status_message(error)

    def calculate(self, formula):
        # replace leading 0 to numbers
        formula = re.sub(r'(?<![\d\.])0*(\d+)', r'\1', formula)
        # replace newlines by spaces
        formula = re.sub(r'\n', ' ', formula)
        result = eval(formula, self.dict, {})
        if isinstance(result, str):
            return result
        else:
            return str(round(result, 13))

    def run_each(self, edit, region, replace=False):
        if not region.empty():
            formula = self.view.substr(region)
            value = self.calculate(formula)
            if value[-2:] == '.0':
                value = value[:-2]
            if not replace:
                value = "%s = %s" % (formula, value)
            self.view.replace(edit, region, value)


class CalculateCountCommand(sublime_plugin.TextCommand):
    def run(self, edit, index=1):
        def generate_integer_counter(initial):
            def count():
                offset = initial
                while True:
                    yield str(offset)
                    offset += 1

            return iter(count()).__next__

        def generate_hexadecimal_counter(initial, length):
            def count():
                offset = initial
                while True:
                    yield u"0x%x" % offset
                    offset += 1

            return iter(count()).__next__

        def generate_octal_counter(initial, length):
            def count():
                offset = initial
                while True:
                    yield u"0%o" % offset
                    offset += 1

            return iter(count()).__next__

        def generate_string_counter(initial):
            def count():
                offset = initial
                while True:
                    yield offset

                    up = 1  # increase last character
                    while True:
                        o = ord(offset[-up])
                        o += 1
                        tail = ''
                        if up > 1:
                            tail = offset[-up + 1:]

                        if o > ord('z'):
                            offset = offset[:-up] + u'a' + tail
                            up += 1
                            if len(offset) < up:
                                offset = u'a' + offset
                                break
                        else:
                            offset = offset[:-up] + chr(o) + tail
                            break

            return iter(count()).__next__

        is_first = True
        subs = []
        for region in self.view.sel():
            if is_first:
                # see if the region is a number or alphanumerics
                content = self.view.substr(region)
                if re.match('0x[0-9a-fA-F]+$', content):
                    counter = generate_hexadecimal_counter(int(content[2:], 16), len(regions))
                elif re.match('0[0-7]+$', content):
                    counter = generate_octal_counter(int(content[1:], 8), len(regions))
                elif re.match('[0-9]+$', content):
                    counter = generate_integer_counter(int(content))
                elif re.match('[a-z]+$', content):
                    counter = generate_string_counter(content)
                else:
                    counter = generate_integer_counter(index)

            subs.append((region, str(counter())))

            is_first = False

        # any edits that are performed will happen in reverse; this makes it
        # easy to keep region.a and region.b pointing to the correct locations
        def get_end(region_tuple):
            return region_tuple[0].end()
        subs.sort(key=get_end, reverse=True)

        for sub in subs:
            self.view.sel().subtract(sub[0])
            self.view.replace(edit, sub[0], sub[1])
            self.view.sel().add(sublime.Region(sub[0].begin() + len(sub[1]), sub[0].begin() + len(sub[1])))
