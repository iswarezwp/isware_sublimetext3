# -*- coding: utf-8 -*-
"""
@author: zhangwenping
Created on 2017-03-10 17:12
"""

import sublime
import sublime_plugin

import string
import datetime
import os.path


class DocstringCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        lang = parse_lang(self.view.file_name())
        if lang is None:
            return

        s = sublime.load_settings("isware.sublime-settings")
        author = s.get('author', 'zhangwenping')
        organization = s.get('organization', 'zhangwenping')

        # get the content of the line
        for region in self.view.sel():
            if region.empty():
                line = self.view.line(region)
                previous_region = sublime.Region(0, line.begin())
                previous_contents = self.view.substr(previous_region)
                if len(previous_contents.strip()) == 0:
                    module_doc = construct_module_docstring(
                        lang, author, organization)
                    self.view.insert(edit, 0, module_doc)

                tab_size = self.view.settings().get("tab_size", 4)
                flag, declaration_region = get_declaration(
                    self.view, line.begin())
                declaration = self.view.substr(declaration_region)
                if flag:
                    # valid declaration
                    result = parse_declaration(declaration)
                    # calculate docstring indent
                    indent = 0
                    try:
                        name = result[1]
                        index = declaration.find(name)
                        if index >= 0:
                            for i in range(index):
                                if declaration[i] == "\t":
                                    indent += tab_size
                                else:
                                    indent += 1
                        docstring = construct_docstring(result, indent=indent)
                        self.view.insert(
                            edit, declaration_region.end() + 2, docstring)
                    except Exception as e:
                        print(e)


def parse_lang(filename):
    """
    only support python and golang
    """
    _, ext = os.path.splitext(filename)
    if ext == ".py":
        return "python"
    elif ext == ".go":
        return "go"


def construct_module_docstring(lang, author, organization):
    """
    @param lang: python / go
    @param author: the author
    @param organization: eg: "Daowoo Co.,Ltd."
    """
    now = datetime.datetime.now()

    if lang == 'python':
        docstring = '# -*- coding: utf-8 -*-\n'
        docstring += '"""\n'
        docstring += 'Copyright (c) %s, %s\n\n'
        docstring += '@author: %s\n'
        docstring += 'Created on %s\n'
        docstring += '"""\n'
    elif lang == 'go':
        docstring = '/**\n'
        docstring += 'Copyright (c) %s, %s\n\n'
        docstring += '@author: %s\n'
        docstring += 'Created on %s\n'
        docstring += '**/\n'

    docstring = docstring % (now.strftime("%Y"),
                             organization,
                             author,
                             now.strftime("%Y-%m-%d %H:%M"))
    return docstring


def construct_docstring(declaration, indent=0):
    '''
    @summary: construct docstring according to the declaration
    @param declaration: the result of parse_declaration() reurns
    @param indent: the indent space number
    '''
    docstring = ""
    try:
        typename, name, params = declaration
        if typename == "class":
            return '    """docstring for %s"""\n' % name
        elif typename == "def":
            lines = []
            lines.append('"""\n')

            param_lines = ['@param %s:\n' % (param)
                           for param in params if len(param)]
            lines.extend(param_lines)

            if len(param_lines):
                lines.append('\n')

            lines.append('@result: \n')
        lines.append('"""\n')

        for line in lines:
            docstring += " " * indent + line

    except Exception as e:
        print(e)

    return docstring


def get_declaration(view, point):
    '''
    @summary: get the whole declaration of the class/def before the
              specified point
    @return: (True/False, region)
            True/False --- if the point in a declaration region
            region --- region of the declaration
    '''
    flag = False
    declaration_region = sublime.Region(0, 0)

    line = view.line(point)
    begin_point = line.begin()
    end_point = line.end()
    while True:
        if begin_point < 0:
            # print("can not find the begin of the declaration")
            flag = False
            break
        line = view.line(begin_point)
        line_contents = view.substr(line)
        words = line_contents.split()
        if len(words) > 0:
            if words[0] in ("class", "def"):
                flag = True
                begin_point = line.begin()
                end_point = line.end()
                break
        # get previous line
        begin_point = begin_point - 1

    if flag:
        # check from the line in where begin_point lives
        line = view.line(end_point)
        line_contents = view.substr(line).rstrip()
        while True:

            if end_point > view.size():
                # print("can not find the end of the declaration")
                flag = False
                break

            if (len(line_contents) >= 2) and (line_contents[-2:] == "):"):
                # print("reach the end of the declaration")
                flag = True
                end_point = line.begin() + len(line_contents) - 1
                break
            # get next line
            line = view.line(end_point + 1)
            end_point = line.end()
            line_contents = view.substr(line).rstrip()

    # check valid
    if end_point <= begin_point:
        flag = False

    # check it again, trip unnessary lines
    if flag:
        declaration_region = sublime.Region(begin_point, end_point)

    return (flag, declaration_region)


def parse_declaration(declaration):
    '''
    @summary: parse the class/def declaration
    @param declaration: class/def declaration string
    @result:
        (typename, name, params)
        typename --- a string specify the type of the declaration,
        must be 'class' or 'def'
        name --- the name of the class/def
        params --- param list
    '''
    def rindex(l, x):
        index = -1
        if len(l) > 0:
            for i in range(len(l) - 1, -1, -1):
                if l[i] == x:
                    index = i
        return index

    typename = ""
    name = ""
    params = []

    tokens = {
        ")": "(",
        "]": "[",
        "}": "{",
    }

    # extract typename
    declaration = declaration.strip()
    if declaration.startswith("class"):
        typename = "class"
        declaration = declaration[len("class"):]
    elif declaration.startswith("def"):
        typename = "def"
        declaration = declaration[len("def"):]
    else:
        typename = "unsupported"

    # extract name
    declaration = declaration.strip()
    index = declaration.find("(")
    if index > 0:
        name = declaration[:index]
        declaration = declaration[index:]
    else:
        name = "can not find the class/def name"

    # process params string
    # the params string are something like "(param1, param2=..)"
    declaration = declaration.strip()
    # print("\nparams string is %s" % (declaration))
    if (len(declaration) >= 2) and (declaration[0] == '(') and \
            (declaration[-1] == ')'):
        # continue process
        declaration = declaration[1:-1].strip()

        stack = []
        for c in declaration:
            if c in string.whitespace:
                if len(stack) > 0:
                    if stack[-1] in string.whitespace:
                        # previous char is whitespace too
                        # so we will discard current whitespace
                        continue
                    else:
                        # push stack
                        stack.append(" ")
                else:
                    # discard leading whitespaces
                    continue
            else:

                if c in tokens.keys():
                    # find the corresponding token
                    index = rindex(stack, tokens[c])
                    # print("c = %s, index = %s" % (c, index))
                    if index > 0:
                        # delete all of the elements between the paired tokens
                        stack = stack[:index]
                else:
                    # push stack
                    stack.append(c)

        tmp = "".join(stack)
        # print("\nstack is: %s" % (tmp))
        # split with ,
        stack = tmp.split(",")
        # print("stack is: %s" % ("".join(stack)))
        params = []
        for w in stack:
            w = w.strip()
            if w == "self":
                # skip self parameter
                continue
            index = w.find("=")
            if index > 0:
                params.append(w[:index].strip())
            else:
                params.append(w)
    else:
        params = []

    return(typename, name, params)
