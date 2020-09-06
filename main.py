import sys
from typing import Dict, List, Any, Union

from antlr4 import *
from gen.CPP14Lexer import CPP14Lexer
from gen.CPP14Parser import CPP14Parser
from gen.CPP14Visitor import CPP14Visitor
import json
import pprint


class MyCPP14Visitor(CPP14Visitor):
    def __init__(self):
        self.mainDictionary = {'children': []}
        self.inClass = 0
        self.inFunction = 0
        self.currentAccessMode = 0  # 0: public, 1: private, 2: protected
        self.currentInsertAddress = []  # where to insert block

    def appendClass(self, class_name):
        """
        To append class dict to main dict
        :param class_name: class_name: name of the class
        :return:
        """
        self.currentInsertAddress.clear()
        # update current insert address as we are in class
        self.currentInsertAddress.append(len(self.mainDictionary['children']))
        class_dictionary = {'attributes': {}, 'children': [], 'name': 'ClassDefinition'}
        class_dictionary['attributes']['name'] = class_name
        self.mainDictionary['children'].append(class_dictionary)

    def getAccessType(self):
        """
        To get current access type
        :return s: string of current access type
        """
        s = ""
        if self.currentAccessMode == 0:
            s += "public"
        elif self.currentAccessMode == 1:
            s += "private"
        else:
            s += "protected"
        return s

    def appendFunction(self, function_name, parameters, return_type_stars):
        """
        To append function dict to main dict and also updates insert address
        :param function_name: function name containing the return type as well
        :param parameters: parameter list
        :param return_type_stars: number of stars in return type
        :return:
        """
        if function_name.find("::") != -1:
            # if the function name has :: then, it is already appended.
            # But, as we are in function now we are updating insert address
            self.currentInsertAddress.clear()
            function_name_split = function_name.split("::")
            class_name = function_name_split[0].strip().split(" ")[-1]
            func_name = function_name_split[1].strip()
            class_idx = -1
            for idx, child in enumerate(self.mainDictionary['children']):
                if child['name'] != 'ClassDefinition':
                    continue
                if child['attributes']['name'] == class_name:
                    class_idx = idx
                    break
            func_idx = -1
            for idx, child in enumerate(self.mainDictionary['children'][class_idx]['children']):
                if child['name'] != 'FunctionDefinition':
                    continue
                if child['attributes']['name'] == func_name:
                    func_idx = idx
                    break
            self.currentInsertAddress.append(class_idx)
            self.currentInsertAddress.append(func_idx)
            self.currentInsertAddress.append(2)
            return
        function_dictionary = {'attributes': {}, 'children': [], 'name': 'FunctionDefinition'}
        return_dictionary = {'attributes': {}, 'name': 'ReturnParameterList'}
        parameters_dictionary = {'children': parameters, 'name': 'ParameterList'}
        block_dictionary = {'children': [], 'name': 'Block'}
        function_dictionary['children'].append(parameters_dictionary)
        function_dictionary['attributes']['visibility'] = self.getAccessType()
        function_name_split = function_name.strip().split(" ")
        if len(function_name_split) == 1:
            function_dictionary['attributes']['name'] = function_name_split[0]
            return_dictionary['attributes']['type'] = 'void' + ' *' * return_type_stars
        else:
            function_dictionary['attributes']['name'] = function_name_split[-1]
            return_dictionary['attributes']['type'] = ' '.join(function_name_split[0:-1]) + ' *' * return_type_stars

        function_dictionary['children'].append(return_dictionary)
        function_dictionary['children'].append(block_dictionary)
        if self.inClass != 0:
            if self.mainDictionary['children'][self.currentInsertAddress[0]]['attributes']['name'] == function_dictionary['attributes']['name']:
                function_dictionary['attributes']['isConstructor'] = 'True'
                function_dictionary['attributes']['kind'] = 'constructor'
            else:
                function_dictionary['attributes']['isConstructor'] = 'False'
                function_dictionary['attributes']['kind'] = 'function'
            self.mainDictionary['children'][self.currentInsertAddress[0]]['children'].append(function_dictionary)
            if self.inFunction:
                self.currentInsertAddress.clear()
                self.currentInsertAddress.append(len(self.mainDictionary['children'])-1)
                self.currentInsertAddress.append(len(self.mainDictionary['children'][self.currentInsertAddress[0]]['children'])-1)
                self.currentInsertAddress.append(2)

        else:
            self.currentInsertAddress.clear()
            for idx, child in enumerate(self.mainDictionary['children']):
                if child['name'] == 'FunctionDefinition' and child['attributes']['name'] == function_dictionary['attributes']['name']:
                    self.currentInsertAddress.append(idx)
                    self.currentInsertAddress.append(2)
                    return
            self.currentInsertAddress.append(len(self.mainDictionary['children']))
            self.currentInsertAddress.append(2)

            function_dictionary['attributes']['isConstructor'] = 'False'
            function_dictionary['attributes']['kind'] = 'function'
            self.mainDictionary['children'].append(function_dictionary)

    def appendStatement(self, statement):
        """
        To append statement dict to main dict
        :param statement: statement to append
        :return:
        """
        temp = self.mainDictionary['children']
        for idx in self.currentInsertAddress:
            temp = temp[idx]['children']
        temp.append(statement)

    def getFunctionParameters(self, ctx: CPP14Parser.FunctiondefinitionContext):
        """
        To get function parameters and return type stars
        :param ctx:
        :return parameters: function parameter list
        :return return_type_stars: number of stars in return type
        """
        return_type_stars = 0
        parameters = []
        parameters_temp1 = ""
        ctx = ctx.children[len(ctx.children) - 2]
        stack = [ctx]
        while len(stack):
            s = stack[-1]
            stack.pop()
            if type(s) is CPP14Parser.PtrdeclaratorContext:
                return_type_stars += 1
            if type(s) is CPP14Parser.ParameterdeclarationclauseContext:
                ctx = s
                break
            if hasattr(s, 'children'):
                if s.children is not None:
                    for node in s.children:
                        stack.append(node)
        stack.clear()
        stack.append(ctx)
        while len(stack):
            s = stack[-1]
            stack.pop()
            if hasattr(s, 'children'):
                if s.children is not None:
                    for node in s.children:
                        stack.append(node)
            else:
                parameters_temp1 = parameters_temp1 + ' ' + s.getText()
        parameters_temp2 = parameters_temp1.split(",")
        for pair in parameters_temp2:
            if pair == '' or len(pair.strip().split(" ")) == 1:
                continue
            func_split = pair.strip().split(" ")
            temp = {}
            for i in func_split:
                if i == '[' or i == ']':
                    continue
                temp['name'] = i
                break
            func_split.reverse()
            temp['type'] = ' '.join(i for i in func_split if i != temp['name'])
            parameters.append(temp)
        parameters.reverse()
        return parameters, return_type_stars - 1

    def getFunctionName(self, ctx: CPP14Parser.FunctiondefinitionContext):
        """
        To get function name and return type
        :param ctx:
        :return: function_name: return type concatenated with function name
        """
        function_name = ''
        # function with no return type
        if len(ctx.children) == 2:
            node = ctx.children[0].children[0].children[0].children[0]
            if self.inClass == 1 and self.inFunction != 1:
                node = node.children[0].children[0]
            function_name += node.getText()
        # function with return type
        else:
            for child in range(len(ctx.children[0].children)):
                function_name += ' ' + ctx.children[0].children[child].getText()
            temp = ctx.children[1].children[0].children[0].children[0]
            if self.inFunction != 1:
                temp = temp.children[0].children[0]
            function_name += ' ' + temp.getText()
        return function_name

    def visitMemberdeclaration(self, ctx: CPP14Parser.MemberdeclarationContext):
        """
        handles several features
        :param ctx:
        :return:
        """
        if len(ctx.children) == 1:
            return self.visitChildren(ctx)
        found = False
        parse_node = ctx.children[len(ctx.children) - 2]
        stack = [parse_node]
        while len(stack):
            s = stack[-1]
            stack.pop()
            if type(s) is CPP14Parser.ParametersandqualifiersContext:
                found = True
                break
            if hasattr(s, 'children'):
                if s.children is not None:
                    for node in s.children:
                        stack.append(node)
        if found:
            parameters, return_type_stars = self.getFunctionParameters(ctx)
            function_name = self.getFunctionName(ctx)
            self.appendFunction(function_name=function_name, parameters=parameters, return_type_stars=return_type_stars)
            return
        #deals with variable declarations of all types (simple variables, arrays, pointers, pointer arrays, initialized variables..  etc)
        elif len(ctx.children) == 3:
                for node in ctx.children[len(ctx.children)-2].children:
                    if node.getText() != ",":
                        if len(node.children) == 1 or len(node.children) == 2:
                            variable_dictionary = {'attributes': {},'children':[], 'name': 'VariableDeclaration'}
                            if type(node) is CPP14Parser.MemberdeclaratorlistContext:
                                node = node.children[0]
                            temp2=node

                            # no pointer variables
                            if len(node.children[0].children[0].children) == 1:

                                #simple variables
                                variable_dictionary['attributes']['type'] = ctx.children[0].getText()
                                variable_dictionary['attributes']['name'] = (node.children[0].children[0].getText())

                                #array condition
                                if len(node.children[0].children[0].children[0].children) == 3 or len(node.children[0].children[0].children[0].children) == 4:
                                    test = node.children[0].children[0].children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()
                            #pointer variables
                            elif len(node.children[0].children[0].children) == 2:
                                h = node.getText()
                                i = 0
                                count = ""
                                while h[i] == '*':
                                    count += ' *'
                                    i += 1
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['type'] += count
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()[i:]
                                node = node.children[0].children[0].children[1]
                                while i > 1:
                                    node = node.children[1]
                                    i -= 1
                                #pointer array condition
                                if len(node.children[0].children) == 3 or len(node.children[0].children) == 4:
                                    test = node.children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            #un initialized variables
                            if len(temp2.children) == 1:
                                variable_dictionary['attributes']['value'] = 'null'
                                variable_dictionary['attributes']['constant'] = 'false'
                                variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                self.appendStatement(variable_dictionary)

                            #initialized variables
                            elif len(temp2.children) == 2:
                                variable_dictionary['attributes']['constant'] = 'false'
                                variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                initialization_dictionary = {'attributes':{},'children':[],'name':"Initialization Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                variable_dictionary['children'].append(initialization_dictionary)
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(variable_dictionary)
                                self.currentInsertAddress.append(0)
                                self.visitChildren(temp2.children[0])
                                self.visitChildren(temp2.children[1].children[1])
                                self.currentInsertAddress.pop()
                                self.currentInsertAddress.pop()
                        #if more than 3 variables are declared in the same statement
                        elif len(node.children) == 3:

                            while len(node.children) == 3:
                                variable_dictionary = {'attributes': {},'children':[], 'name': 'VariableDeclaration'}
                                temp = node.children[2]
                                if type(temp) is CPP14Parser.MemberdeclaratorlistContext:
                                    temp = temp.children[0]
                                temp2 = temp

                                #no pointer variables
                                if len(temp.children[0].children[0].children) == 1:

                                    #simple variables condition
                                    variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                    variable_dictionary['attributes']['name'] = temp.children[0].children[0].getText()

                                    #array condition
                                    if len(temp.children[0].children[0].children[0].children) == 3 or len(temp.children[0].children[0].children[0].children) == 4:
                                        test = temp.children[0].children[0].children[0]
                                        while len(test.children) == 3 or len(test.children) == 4:
                                            test = test.children[0]
                                        variable_dictionary['attributes']['type'] += "array"
                                        variable_dictionary['attributes']['name'] = test.getText()
                                #pointer variables
                                elif len(temp.children[0].children[0].children) == 2:
                                    h = temp.getText()
                                    i = 0
                                    count = ""
                                    while h[i] == '*':
                                        count += ' *'
                                        i += 1
                                    variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                    variable_dictionary['attributes']['type'] += count
                                    variable_dictionary['attributes']['name'] = temp.children[0].children[0].getText()[i:]
                                    temp = temp.children[0].children[0].children[1]
                                    while i > 1:
                                        temp = temp.children[1]
                                        i -= 1
                                    # pointer array condition
                                    if len(temp.children[0].children) == 3 or len(temp.children[0].children) == 4:
                                        test = temp.children[0]
                                        while len(test.children) == 3 or len(test.children) == 4:
                                            test = test.children[0]
                                        variable_dictionary['attributes']['type'] += "array"
                                        variable_dictionary['attributes']['name'] = test.getText()
                                #un initialized variables
                                if len(temp2.children) == 1:
                                    variable_dictionary['attributes']['value'] = 'null'
                                    variable_dictionary['attributes']['constant'] = 'false'
                                    variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                    self.appendStatement(variable_dictionary)
                                #initialized variables
                                elif len(temp2.children) == 2:
                                    variable_dictionary['attributes']['constant'] = 'false'
                                    variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                    initialization_dictionary = {'attributes': {}, 'children': [],'name': "Initialization Statement"}
                                    initialization_dictionary['attributes']['operator'] = "="
                                    variable_dictionary['children'].append(initialization_dictionary)

                                    temp = self.mainDictionary['children']
                                    for idx in self.currentInsertAddress:
                                        temp = temp[idx]['children']
                                    self.currentInsertAddress.append(len(temp))
                                    temp.append(variable_dictionary)
                                    self.currentInsertAddress.append(0)
                                    self.visitChildren(temp2.children[0])
                                    self.visitChildren(temp2.children[1].children[1])
                                    self.currentInsertAddress.pop()
                                    self.currentInsertAddress.pop()
                                node = node.children[0]

                            # after the above while loop for the last remaining variable
                            variable_dictionary = {'attributes': {},'children':[],'name': 'VariableDeclaration'}
                            if type(node) is CPP14Parser.MemberdeclaratorlistContext:
                                node = node.children[0]
                            temp2 = node
                            #no pointer variables condition
                            if len(node.children[0].children[0].children) == 1:

                                #simple variables condition
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()

                                #array condition
                                if len(node.children[0].children[0].children[0].children) == 3 or len(node.children[0].children[0].children[0].children) == 4:
                                    test = node.children[0].children[0].children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            # pointer variables condition
                            elif len(node.children[0].children[0].children) == 2:
                                h = node.getText()
                                i = 0
                                count = ""
                                while h[i] == '*':
                                    count += ' *'
                                    i += 1
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['type'] += count
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()[i:]
                                node = node.children[0].children[0].children[1]
                                while i > 1:
                                    node = node.children[1]
                                    i -= 1

                                #pointer array condition
                                if len(node.children[0].children) == 3 or len(node.children[0].children) == 4:
                                    test = node.children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            #un initialized variables
                            if len(temp2.children) == 1:
                                variable_dictionary['attributes']['value'] = 'null'
                                variable_dictionary['attributes']['constant'] = 'false'
                                variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                self.appendStatement(variable_dictionary)

                            # initialized variables
                            elif len(temp2.children) == 2:
                                variable_dictionary['attributes']['constant'] = 'false'
                                variable_dictionary['attributes']['visibility'] = self.getAccessType()
                                initialization_dictionary = {'attributes':{},'children':[],'name':"Initialization Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                variable_dictionary['children'].append(initialization_dictionary)
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(variable_dictionary)
                                self.currentInsertAddress.append(0)
                                self.visitChildren(temp2.children[0])
                                self.visitChildren(temp2.children[1].children[1])
                                self.currentInsertAddress.pop()
                                self.currentInsertAddress.pop()

        # deals with expressions like a=2,arr[]={1,2,3}(i.e assignment expressions inside class and outside functions)
        elif len(ctx.children) == 2:
            for node in ctx.children[0].children:
                if node.getText()!=",":
                    if len(node.children) == 3:
                        while len(node.children) == 3:
                            temp2=node.children[2]
                            if type(temp2) is CPP14Parser.MemberdeclaratorlistContext:
                                temp2=temp2.children[0]
                            if len(temp2.children)==2 and type(temp2.children[1]) is CPP14Parser.BraceorequalinitializerContext:
                                initialization_dictionary = {'attributes': {}, 'children': [],'name': "Initialization Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(initialization_dictionary)
                                self.visitChildren(temp2.children[0])
                                self.visitChildren(temp2.children[1].children[1])
                                self.currentInsertAddress.pop()
                            node=node.children[0]
                        if type(node) is CPP14Parser.MemberdeclaratorlistContext:
                            node = node.children[0]
                        if len(node.children) == 2 and type(node.children[1]) is CPP14Parser.BraceorequalinitializerContext:
                            initialization_dictionary = {'attributes': {}, 'children': [],'name': "Initialization Statement"}
                            initialization_dictionary['attributes']['operator'] = "="
                            temp = self.mainDictionary['children']
                            for idx in self.currentInsertAddress:
                                temp = temp[idx]['children']
                            self.currentInsertAddress.append(len(temp))
                            temp.append(initialization_dictionary)
                            self.visitChildren(node.children[0])
                            self.visitChildren(node.children[1].children[1])
                            self.currentInsertAddress.pop()
                    elif (len(node.children) == 2 and type(node.children[1]) is CPP14Parser.BraceorequalinitializerContext) or len(node.children)==1:
                        if len(node.children)==1:
                            if type(node) is CPP14Parser.MemberdeclaratorlistContext:
                                node=node.children[0]
                        initialization_dictionary = {'attributes': {}, 'children': [], 'name': "Initialization Statement"}
                        initialization_dictionary['attributes']['operator'] = "="
                        temp = self.mainDictionary['children']
                        for idx in self.currentInsertAddress:
                            temp = temp[idx]['children']
                        self.currentInsertAddress.append(len(temp))
                        temp.append(initialization_dictionary)
                        self.visitChildren(node.children[0])
                        self.visitChildren(node.children[1].children[1])
                        self.currentInsertAddress.pop()

    def visitSimpledeclaration(self, ctx: CPP14Parser.SimpledeclarationContext):
        """
        handles several features
        :param ctx:
        :return:
        """
        if len(ctx.children) == 2 and type(ctx.children[0]) is not CPP14Parser.InitdeclaratorlistContext:
            self.inClass = 1
            self.currentAccessMode = 1
            self.appendClass(ctx.children[0].children[0].children[0].children[0].children[0].children[1].getText())
            self.visitChildren(ctx)
            self.currentAccessMode = 0
            self.inClass = 0
            return
        else:
            found = False
            parse_node = ctx.children[len(ctx.children) - 2]
            stack = [parse_node]
            while len(stack):
                s = stack[-1]
                stack.pop()
                if type(s) is CPP14Parser.ParametersandqualifiersContext:
                    found = True
                    break
                if hasattr(s, 'children'):
                    if s.children is not None:
                        for node in s.children:
                            stack.append(node)
            if found:
                parameters, return_type_stars = self.getFunctionParameters(ctx)
                function_name = self.getFunctionName(ctx)
                self.appendFunction(function_name=function_name, parameters=parameters,
                                    return_type_stars=return_type_stars)
            # deals with variable declarations of all types (simple variables, arrays, pointers, pointer arrays, initialized variables..  etc)
            elif len(ctx.children) == 3:
                for node in ctx.children[1].children:
                    if node.getText() != ",":
                        if len(node.children) == 1 or len(node.children) == 2:
                            variable_dictionary = {'attributes': {},'children':[], 'name': 'VariableDeclaration'}
                            if type(node) is CPP14Parser.InitdeclaratorlistContext:
                                node=node.children[0]
                            temp2 = node

                            # no pointers condition
                            if len(node.children[0].children[0].children) == 1:
                                #simple variable condition
                                variable_dictionary['attributes']['type'] = ctx.children[0].getText()
                                variable_dictionary['attributes']['name'] = (node.children[0].children[0].getText())

                                # array condition
                                if len(node.children[0].children[0].children[0].children) == 3 or len(node.children[0].children[0].children[0].children) == 4:
                                    test = node.children[0].children[0].children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            #pointer variables condition
                            elif len(node.children[0].children[0].children) == 2:
                                h = node.getText()
                                i = 0
                                count = ""
                                while h[i] == '*':
                                    count += '*'
                                    i += 1
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['type'] += count
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()[i:]
                                node = node.children[0].children[0].children[1]
                                while i > 1:
                                    node = node.children[1]
                                    i-=1

                                # pointer array condition
                                if len(node.children[0].children) == 3 or len(node.children[0].children) == 4:
                                    test = node.children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            # un initialized variables
                            if len(temp2.children) == 1:
                                variable_dictionary['attributes']['value'] = 'null'
                                variable_dictionary['attributes']['constant'] = 'false'
                                if self.inFunction:
                                    variable_dictionary['attributes']['visibility'] = 'private'
                                else:
                                    variable_dictionary['attributes']['visibility'] = 'public'
                                self.appendStatement(variable_dictionary)

                            # initialized  variables
                            elif len(temp2.children) == 2:
                                variable_dictionary['attributes']['constant'] = 'false'
                                if self.inFunction:
                                    variable_dictionary['attributes']['visibility'] = 'private'
                                else:
                                    variable_dictionary['attributes']['visibility'] = 'public'
                                initialization_dictionary = {'attributes':{},'children':[],'name':"Initialization Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                variable_dictionary['children'].append(initialization_dictionary)
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(variable_dictionary)
                                self.currentInsertAddress.append(0)
                                self.visitChildren(temp2.children[0])
                                self.visitChildren(temp2.children[1].children[0].children[1])
                                self.currentInsertAddress.pop()
                                self.currentInsertAddress.pop()
                        # if more than 2 variables are declared at a time
                        elif len(node.children) == 3:

                            while len(node.children) == 3:
                                variable_dictionary = {'attributes': {},'children':[], 'name': 'VariableDeclaration'}
                                temp = node.children[2]
                                if type(temp) is CPP14Parser.InitdeclaratorlistContext:
                                    temp=temp.children[0]
                                temp2=temp

                                #no pointers condition
                                if len(temp.children[0].children[0].children) == 1:

                                    #simple variables
                                    variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                    variable_dictionary['attributes']['name'] = temp.children[0].children[0].getText()

                                    #array condition
                                    if len(temp.children[0].children[0].children[0].children)==3 or len(temp.children[0].children[0].children[0].children)==4:#array condition
                                        test = temp.children[0].children[0].children[0]
                                        while len(test.children) == 3 or len(test.children) == 4:
                                            test = test.children[0]
                                        variable_dictionary['attributes']['type'] += "array"
                                        variable_dictionary['attributes']['name'] = test.getText()

                                #pointer variables condition
                                elif len(temp.children[0].children[0].children) == 2:
                                    h = temp.getText()
                                    i = 0
                                    count = ""
                                    while h[i] == '*':
                                        count += '*'
                                        i += 1
                                    variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                    variable_dictionary['attributes']['type'] += count
                                    variable_dictionary['attributes']['name'] = temp.children[0].children[0].getText()[i:]
                                    temp=temp.children[0].children[0].children[1]
                                    while i>1:
                                        temp=temp.children[1]
                                        i-=1

                                    # pointer array condition
                                    if len(temp.children[0].children) ==3 or len(temp.children[0].children) ==4:
                                        test=temp.children[0]
                                        while len(test.children) == 3 or len(test.children) == 4:
                                            test=test.children[0]
                                        variable_dictionary['attributes']['type'] += "array"
                                        variable_dictionary['attributes']['name'] = test.getText()

                                # un initialized variables
                                if len(temp2.children) == 1:
                                    variable_dictionary['attributes']['value'] = 'null'
                                    variable_dictionary['attributes']['constant'] = 'false'
                                    if self.inFunction:
                                        variable_dictionary['attributes']['visibility'] = 'private'
                                    else:
                                        variable_dictionary['attributes']['visibility'] = 'public'
                                    self.appendStatement(variable_dictionary)

                                #initialized variables
                                elif len(temp2.children) == 2:
                                    variable_dictionary['attributes']['constant'] = 'false'
                                    if self.inFunction:
                                        variable_dictionary['attributes']['visibility'] = 'private'
                                    else:
                                        variable_dictionary['attributes']['visibility'] = 'public'
                                    initialization_dictionary = {'attributes': {}, 'children': [],'name': "Initialization Statement"}
                                    initialization_dictionary['attributes']['operator'] = "="
                                    variable_dictionary['children'].append(initialization_dictionary)
                                    temp = self.mainDictionary['children']
                                    for idx in self.currentInsertAddress:
                                        temp = temp[idx]['children']
                                    self.currentInsertAddress.append(len(temp))
                                    temp.append(variable_dictionary)
                                    self.currentInsertAddress.append(0)
                                    self.visitChildren(temp2.children[0])
                                    self.visitChildren(temp2.children[1].children[0].children[1])
                                    self.currentInsertAddress.pop()
                                    self.currentInsertAddress.pop()
                                node = node.children[0]

                            #after the above while loop for the last remaining variable
                            variable_dictionary = {'attributes': {},'children':[], 'name': 'VariableDeclaration'}
                            if type(node) is CPP14Parser.InitdeclaratorlistContext:
                                    node = node.children[0]
                            temp2 = node

                            #no pointer variables
                            if len(node.children[0].children[0].children) == 1:

                                #simple variable condition
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()

                                #array condition
                                if len(node.children[0].children[0].children[0].children) == 3 or len(node.children[0].children[0].children[0].children) == 4:
                                    test = node.children[0].children[0].children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            #pointer variables
                            elif len(node.children[0].children[0].children) == 2:
                                h = node.getText()
                                i = 0
                                count = ""
                                while h[i] == '*':
                                    count += '*'
                                    i += 1
                                variable_dictionary['attributes']['type'] = (ctx.children[0].getText())
                                variable_dictionary['attributes']['type'] += count
                                variable_dictionary['attributes']['name'] = node.children[0].children[0].getText()[i:]
                                node = node.children[0].children[0].children[1]
                                while i > 1:
                                    node = node.children[1]
                                    i-=1

                                #pointer array condition
                                if len(node.children[0].children) == 3 or len(node.children[0].children) == 4:
                                    test = node.children[0]
                                    while len(test.children) == 3 or len(test.children) == 4:
                                        test = test.children[0]
                                    variable_dictionary['attributes']['type'] += "array"
                                    variable_dictionary['attributes']['name'] = test.getText()

                            #un initialized variables
                            if len(temp2.children) == 1:
                                variable_dictionary['attributes']['value'] = 'null'
                                variable_dictionary['attributes']['constant'] = 'false'
                                if self.inFunction:
                                    variable_dictionary['attributes']['visibility'] = 'private'
                                else:
                                    variable_dictionary['attributes']['visibility'] = 'public'
                                self.appendStatement(variable_dictionary)

                            #initialized variables
                            elif len(temp2.children) == 2:
                                variable_dictionary['attributes']['constant'] = 'false'
                                if self.inFunction:
                                    variable_dictionary['attributes']['visibility'] = 'private'
                                else:
                                    variable_dictionary['attributes']['visibility'] = 'public'
                                initialization_dictionary = {'attributes':{},'children':[],'name':"Initialization Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                variable_dictionary['children'].append(initialization_dictionary)
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(variable_dictionary)
                                self.currentInsertAddress.append(0)
                                self.visitChildren(temp2.children[0])
                                self.visitChildren(temp2.children[1].children[0].children[1])
                                self.currentInsertAddress.pop()
                                self.currentInsertAddress.pop()

            # deals with expressions like a=2,arr[]={1,2,3}(i.e assignment expressions outside class and outside functions)
            elif len(ctx.children) == 2 and type(ctx.children[0]) is CPP14Parser.InitdeclaratorlistContext:
                for node in ctx.children[0].children:
                    if node.getText() != ",":
                        if len(node.children) == 3:
                            while len(node.children) == 3:
                                temp2 = node.children[2]
                                if type(temp2) is CPP14Parser.InitdeclaratorlistContext:
                                    temp2 = temp2.children[0]
                                if len(temp2.children) == 2 and type(temp2.children[1].children[0]) is CPP14Parser.BraceorequalinitializerContext:
                                    initialization_dictionary = {'attributes': {}, 'children': [],'name': "Assignment Statement"}
                                    initialization_dictionary['attributes']['operator'] = "="
                                    temp = self.mainDictionary['children']
                                    for idx in self.currentInsertAddress:
                                        temp = temp[idx]['children']
                                    self.currentInsertAddress.append(len(temp))
                                    temp.append(initialization_dictionary)
                                    self.visitChildren(temp2.children[0])
                                    self.visitChildren(temp2.children[1].children[0].children[1])
                                    self.currentInsertAddress.pop()
                                node = node.children[0]
                            if type(node) is CPP14Parser.InitdeclaratorlistContext:
                                node = node.children[0]
                            if len(node.children) == 2 and type(node.children[1].children[0]) is CPP14Parser.BraceorequalinitializerContext:
                                initialization_dictionary = {'attributes': {}, 'children': [],'name': "Assignment Statement"}
                                initialization_dictionary['attributes']['operator'] = "="
                                temp = self.mainDictionary['children']
                                for idx in self.currentInsertAddress:
                                    temp = temp[idx]['children']
                                self.currentInsertAddress.append(len(temp))
                                temp.append(initialization_dictionary)
                                self.visitChildren(node.children[0])
                                self.visitChildren(node.children[1].children[0].children[1])
                                self.currentInsertAddress.pop()
                        elif (len(node.children) == 2 and type(node.children[1].children[0]) is CPP14Parser.BraceorequalinitializerContext) or len(node.children) == 1:
                            if len(node.children) == 1:
                                if type(node) is CPP14Parser.InitdeclaratorlistContext:
                                    node = node.children[0]
                            initialization_dictionary = {'attributes': {}, 'children': [],'name': "Assignment Statement"}
                            initialization_dictionary['attributes']['operator'] = "="
                            temp = self.mainDictionary['children']
                            for idx in self.currentInsertAddress:
                                temp = temp[idx]['children']
                            self.currentInsertAddress.append(len(temp))
                            temp.append(initialization_dictionary)
                            self.visitChildren(node.children[0])
                            self.visitChildren(node.children[1].children[0].children[1])
                            self.currentInsertAddress.pop()


    def visitAssignmentexpression(self, ctx: CPP14Parser.AssignmentexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            assignment_expression_dictionary = {'attributes': {}, 'children': [], 'name': 'AssignmentExpression'}
            assignment_expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(assignment_expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitPmexpression(self, ctx: CPP14Parser.PmexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'PMExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitMultiplicativeexpression(self, ctx: CPP14Parser.MultiplicativeexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'MultiplicativeExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitAdditiveexpression(self, ctx: CPP14Parser.AdditiveexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'AdditiveExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitShiftexpression(self, ctx: CPP14Parser.ShiftexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'ShiftExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitRelationalexpression(self, ctx: CPP14Parser.RelationalexpressionContext):
        """
         Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'RelationalExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitEqualityexpression(self, ctx: CPP14Parser.EqualityexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'EqualityExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitAndexpression(self, ctx: CPP14Parser.AndexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'AndExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitExclusiveorexpression(self, ctx: CPP14Parser.ExclusiveorexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'ExclusiveOrExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitInclusiveorexpression(self, ctx: CPP14Parser.InclusiveorexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'InclusiveOrExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    # Visit a parse tree produced by CPP14Parser#logicalandexpression.
    def visitLogicalandexpression(self, ctx: CPP14Parser.LogicalandexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'LogicalAndExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitLogicalorexpression(self, ctx: CPP14Parser.LogicalorexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'LogicalOrExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[0])
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitPrimaryexpression(self, ctx: CPP14Parser.PrimaryexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 3:
            expression_dictionary = {'children': [], 'name': 'PrimaryExpression'}
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[1])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitPostfixexpression(self, ctx: CPP14Parser.PostfixexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 1:
            return self.visitChildren(ctx)
        else:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'PostFixExpression'}
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            if len(ctx.children) == 2:
                expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
                self.visitChildren(ctx.children[0])
            elif len(ctx.children) == 3:
                expression_dictionary['attributes']['operator'] = ctx.children[1].getText()
                self.visitChildren(ctx.children[0])
                self.visitChildren(ctx.children[1])
            elif len(ctx.children) == 4:
                string = ""
                if ctx.children[1].getText() == '[':
                    string += "ArrayAccess"
                else:
                    if type(ctx.children[0]) is CPP14Parser.SimpletypespecifierContext:
                        string += "ElementaryOperation"
                    else:
                        string += "FunctionCall"
                expression_dictionary['attributes']['operator'] = string
                self.visitChildren(ctx)
            self.currentInsertAddress.pop()

    def visitUnaryexpression(self, ctx: CPP14Parser.UnaryexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 1:
            return self.visitChildren(ctx)
        else:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'UnaryExpression'}
            expression_dictionary['attributes']['operator'] = ctx.children[0].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            if len(ctx.children) == 2:
                self.visitChildren(ctx.children[1])
            elif len(ctx.children) == 4:
                self.visitChildren(ctx)
            else:
                identifier_dictionary = {'attributes': {}, 'name': 'Identifier'}
                identifier_dictionary['attributes']['name'] = ctx.children[3].getText()
                expression_dictionary['children'].append(identifier_dictionary)
            self.currentInsertAddress.pop()

    def visitCastexpression(self, ctx: CPP14Parser.CastexpressionContext):
        """
        Appends expression_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) == 4:
            expression_dictionary = {'attributes': {}, 'children': [], 'name': 'CastExpression'}
            expression_dictionary['attributes']['type'] = ctx.children[1].getText()
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(expression_dictionary)
            self.visitChildren(ctx.children[3])
            self.currentInsertAddress.pop()
        else:
            return self.visitChildren(ctx)

    def visitUnqualifiedid(self, ctx: CPP14Parser.UnqualifiedidContext):
        """
        Appends identifier_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        identifier_dictionary = {'attributes': {}, 'name': 'Identifier'}
        identifier_dictionary['attributes']['name'] = ctx.getText()
        self.appendStatement(identifier_dictionary)

    def visitLiteral(self, ctx: CPP14Parser.LiteralContext):
        """
        Appends literal_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        literal_dictionary = {'attributes': {}, 'name': 'Literal'}
        literal_dictionary['attributes']['name'] = ctx.getText()
        self.appendStatement(literal_dictionary)

    def visitSimpletypespecifier(self, ctx: CPP14Parser.SimpletypespecifierContext):
        """
        Appends simple_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        simple_dictionary = {'attributes': {}, 'name': 'SimpleTypeSpecifier'}
        simple_dictionary['attributes']['name'] = ctx.getText()
        self.appendStatement(simple_dictionary)

    def visitThetypeid(self, ctx: CPP14Parser.ThetypeidContext):
        """
        Appends type_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        type_dictionary = {'attributes': {}, 'name': 'Type'}
        type_dictionary['attributes']['name'] = ctx.getText()
        self.appendStatement(type_dictionary)

    def visitConditionalexpression(self, ctx: CPP14Parser.ConditionalexpressionContext):
        """
        Appends selection_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        if len(ctx.children) > 1:
            selection_dictionary = {'children': [{'children': [], 'name': 'Condition'}],
                                    'name': 'ConditionalExpression'}
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            selection_dictionary['children'].append({'name': 'If', 'children': []})
            selection_dictionary['children'].append({'name': 'Else', 'children': []})
            temp.append(selection_dictionary)
            # For condition
            self.currentInsertAddress.append(0)
            self.visitChildren(ctx.children[0])
            self.currentInsertAddress.pop()
            # For if
            self.currentInsertAddress.append(1)
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
            # For else
            self.currentInsertAddress.append(2)
            self.visitChildren(ctx.children[4])
            self.currentInsertAddress.pop()
            # Out of selection dictionary
            self.currentInsertAddress.pop()

        else:
            return self.visitChildren(ctx)

    def visitFunctiondefinition(self, ctx: CPP14Parser.FunctiondefinitionContext):
        """
        Visits function body and helps in appending function to main_dictionary
        :param ctx:
        :return:
        """
        self.inFunction = 1
        parameters, return_type_stars = self.getFunctionParameters(ctx)
        function_name = self.getFunctionName(ctx)
        self.appendFunction(function_name=function_name, parameters=parameters, return_type_stars=return_type_stars)
        # visit function body
        self.visitChildren(ctx.children[len(ctx.children) - 1])
        self.inFunction = 0
        return

    def visitAccessspecifier(self, ctx: CPP14Parser.AccessspecifierContext):
        """
        Stores access specifier
        :param ctx:
        :return:
        """
        access = ctx.getText()
        if access == 'public':
            self.currentAccessMode = 0
        elif access == 'private':
            self.currentAccessMode = 1
        else:
            self.currentAccessMode = 2
        return self.visitChildren(ctx)

    def visitJumpstatement(self, ctx: CPP14Parser.JumpstatementContext):
        """
        Appends jump_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        jump_dictionary = {'type': 'JumpStatement', 'name': ctx.children[0].getText()}
        # For break, continue
        if len(ctx.children) == 2:
            self.appendStatement(jump_dictionary)
        # For return
        else:
            jump_dictionary['children'] = []
            temp = self.mainDictionary['children']
            for idx in self.currentInsertAddress:
                temp = temp[idx]['children']
            self.currentInsertAddress.append(len(temp))
            temp.append(jump_dictionary)
            self.visitChildren(ctx)
            self.currentInsertAddress.pop()

    def visitIterationstatement(self, ctx: CPP14Parser.IterationstatementContext):
        """
        Appends iteration_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        iteration_dictionary = {}
        temp = self.mainDictionary['children']
        for idx in self.currentInsertAddress:
            temp = temp[idx]['children']
        self.currentInsertAddress.append(len(temp))
        temp.append(iteration_dictionary)
        # For while
        if ctx.children[0].getText() == 'while':
            iteration_dictionary['name'] = 'WhileBlock'
            iteration_dictionary['children'] = [{'children': [], 'name': 'WhileCondition'},
                                                {'children': [], 'name': 'WhileLoopStatements'}]
            # While Condition
            self.currentInsertAddress.append(0)
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
            # While Statements
            self.currentInsertAddress.append(1)
            self.visitChildren(ctx.children[4])
            self.currentInsertAddress.pop()
        # For do-while
        elif ctx.children[0].getText() == 'do':
            iteration_dictionary['name'] = 'DoWhileBlock'
            iteration_dictionary['children'] = [{'children': [], 'name': 'DoWhileCondition'},
                                                {'children': [], 'name': 'DoWhileLoopStatements'}]
            # Do-While Condition
            self.currentInsertAddress.append(0)
            self.visitChildren(ctx.children[4])
            self.currentInsertAddress.pop()
            # Do-While Statements
            self.currentInsertAddress.append(1)
            self.visitChildren(ctx.children[1])
            self.currentInsertAddress.pop()
        # For for
        else:
            iteration_dictionary['name'] = 'ForBlock'
            iteration_dictionary['children'] = [{'children': [], 'name': 'ForInit'},
                                                {'children': [], 'name': 'ForCondition'},
                                                {'children': [], 'name': 'ForExpression'},
                                                {'children': [], 'name': 'ForLoopStatements'}]
            # For init
            self.currentInsertAddress.append(0)
            self.visitChildren(ctx.children[2])
            self.currentInsertAddress.pop()
            temp1 = 4
            if ctx.children[4].getText() == ';':
                temp1 = temp1 + 1
                # For Condition
                self.currentInsertAddress.append(1)
                self.visitChildren(ctx.children[3])
                self.currentInsertAddress.pop()
            # For Expression
            self.currentInsertAddress.append(2)
            self.visitChildren(ctx.children[temp1])
            self.currentInsertAddress.pop()
            # For Statements
            self.currentInsertAddress.append(3)
            self.visitChildren(ctx.children[-1])
            self.currentInsertAddress.pop()
        # out of iterative statement
        self.currentInsertAddress.pop()

    def visitUsingdirective(self, ctx: CPP14Parser.UsingdirectiveContext):
        """
        Appends the using_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        using_dictionary = {'namespace': ctx.children[2].getText(), 'name': 'UsingDirective'}
        self.mainDictionary['children'].append(using_dictionary)
        return

    def visitSelectionstatement(self, ctx: CPP14Parser.SelectionstatementContext):
        """
        Appends selection_dictionary to the main_dictionary
        :param ctx:
        :return:
        """
        selection_dictionary = {'children': [{'children': [], 'name': 'Condition'}], 'name': 'SelectionStatement'}
        temp = self.mainDictionary['children']
        for idx in self.currentInsertAddress:
            temp = temp[idx]['children']
        self.currentInsertAddress.append(len(temp))
        selection_dictionary['children'].append({'name': 'IfBlock', 'children': []})
        temp.append(selection_dictionary)
        # For condition
        self.currentInsertAddress.append(0)
        self.visitChildren(ctx.children[2])
        self.currentInsertAddress.pop()
        # For if block
        self.currentInsertAddress.append(1)
        self.visitChildren(ctx.children[4])
        self.currentInsertAddress.pop()
        # Done for only if block
        # both if-else
        if len(ctx.children) != 5:
            selection_dictionary['children'].append({'name': 'ElseBlock', 'children': []})
            # For else block
            self.currentInsertAddress.append(2)
            self.visitChildren(ctx.children[6])
            self.currentInsertAddress.pop()
        # out of selection statement
        self.currentInsertAddress.pop()


def main(argv):
    i = FileStream(argv[1])
    lexer = CPP14Lexer(i)
    stream = CommonTokenStream(lexer)
    parser = CPP14Parser(stream)
    tree = parser.translationunit()

    v = MyCPP14Visitor()
    v.visit(tree)

    # using pretty print to display the resultatnt JSON
    pprint.pprint(v.mainDictionary)

    json_string = json.dumps(v.mainDictionary)
    with open("output.txt", "w") as outfile:
        outfile.write(json_string)


if __name__ == '__main__':
    main(sys.argv)
