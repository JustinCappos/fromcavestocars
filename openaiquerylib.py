#!/usr/bin/python3
"""
This serves as the query API for OpenAI's ChatGPT model.   It handles caching
and also does things like parse responses so they are easier to work with.

I'll use ChatGPT to help me write parts of this library as well.
"""

import openai

# for (de-)serializing data so that I don't redo all queries, all the time.
import json


DEFAULTCACHEFILE = "openai.cache.json"

MAX_ITEMS_PER_QUERY = 20

from os.path import exists

def join_with_quotes_and_commas(strings,combinerword="and"):
    if not strings:
        return ""
    elif len(strings) == 1:
        return f'"{strings[0]}"'
    elif len(strings) == 2:
        return f'"{strings[0]}" {combinerword} "{strings[1]}"'
    else:
        return ', '.join(f'"{s}"' for s in strings[:-1]) + f', {combinerword} "{strings[-1]}"'


class OpenAIQuery:

    def __init__(self, cachefile = DEFAULTCACHEFILE, model = "gpt-4o-mini-2024-07-18",create_if_needed=False):
        if cachefile:
            # if I need to create it, do so.
            if exists(cachefile): # from os.path
                self.load_but_do_not_enable_cache(cachefile)
            else:
                self.empty_cache()
            self.fully_enable_cache(cachefile)
        else:
            # I'll have the cache contain a 'raw' dict for the actual queries
            # and responses, and a 'list' dict for queries which ask about a
            # list of items.   
            # The 'raw' will contain everything I ask, but the 'list' is for
            # more efficient lookups of specialized data.  The 'list' is 
            # indexed by the list item and then sub indexed by the query
            # So list queries: "Are any of these a vegetable?" ['carrot'] and
            # "Are any of these a mineral?" ['carrot'] will result in a list
            # dictionary of {'carrot':{"Are any of these a vegetable?":,"yes",
            # "Are any of these a mineral?":'no'}}
            # my rationale for this structure is that you'll usually know the
            # items you want to query when asking a query, but you may not
            # know all of the queries you asked for an item.
            self.empty_cache()
            self.fully_disable_cache()

        self.model = model


    def empty_cache(self):
        """ Empty out the cache.   Does not write the cache to disk or enable/
            disable the cache"""
        self.cache = {'raw':{},'list':{},'kb':{}}


    def fully_disable_cache(self):
        """ Stops updating the cache or checking it.   Does not delete the 
            cache file on disk."""
        self.updatecache = False
        self.checkcache = False
        self.autoflushcache = False

    def load_but_do_not_enable_cache(self, cachefile):
        """ Loads the cache from disk """
        self.cache = json.load(open(cachefile))
        # add keys which may be missing...  This likely only occurs when either
        # using a blank file or changing formats...
        if 'kb' not in self.cache:
            self.cache['kb'] = {}
        if 'raw' not in self.cache:
            self.cache['raw'] = {}
        if 'list' not in self.cache:
            self.cache['list'] = {}

    def fully_enable_cache(self, cachefile):
        """ Starts updating the cache and checking it for queries."""
        self.cachefile = cachefile
        self.updatecache = True
        self.checkcache = True
        self.autoflushcache = True

    def write_cache_to_disk(self):
        """ Flush the cache to disk."""
        # I'll indent so it is at least somewhat readable...   I probably
        # should let my editor do this though...
        json.dump(self.cache,open(self.cachefile,"w"),indent=4)


    # I could have a 'stream' for queries, if I wanted to keep state, as 
    # ChatGPT does in the web interface.  I'll skip this for now, but could 
    # imagine wanting to play with this later.

    def do_query(self, querystring,optionalprefix = ''):
        """ Used to do an OpenAI query.   It will cache the result (by default)
        so that if you repeat it, you just get the prior result back.   It 
        flushes the cache to disk on every request.

        The optionalprefix argument is meant to be used if you want to slightly
        refine a query later, but do not want to re-run older versions.   Old
        responses will be cached and used, but new queries will contain it.

        I wrote this by hand"""

        # return the result, if we know it.
        if self.checkcache and querystring in self.cache['raw']:
            return self.cache['raw'][querystring]

        # This doesn't seem to have any cost other than local parsing.  I'll 
        # recreate this per-request...
        client = openai.OpenAI()

        transmittedquery = optionalprefix + querystring

        # This will raise exceptions, which I likely should catch...
        completion = client.chat.completions.create(
            model=self.model,
            messages=[
                ###{"role": "system", "content": "You are a helpful assistant."},
                # As I understand it, the system role for queries is just a way to 
                # give instructions that don't fall into the user query field.  So 
                # you can view this as a way to try to control what the user query 
                # can actually do.   
                #
                # Since I'm not doing any of this, it doesn't matter for me.   
                # I'll just skip this.   
                { "role": "user", "content": transmittedquery }
            ]
        )

        if len(completion.choices) != 1:
            # I think this should happen because the examples seem to imply it will.
            print(transmittedquery,"Did not get exactly 1 choice, as expected:",completion.choices)

        if completion.choices[0].finish_reason != "stop":
            print(transmittedquery,"Finished because of '"+completion.choices[0].finish_reason+"'.")

        result = completion.choices[0].message.content

        if self.updatecache:
            self.cache['raw'][querystring] = result
            if self.autoflushcache:
                self.write_cache_to_disk()

        return result



    def do_query_with_list_arguments(self, querystring, listofitems, optionalprefix =''):
        """ Used to do an OpenAI query which ends with a list.   For example,
        "Which of the following are vegetables:", ['carrot', 'banana', 'cow']

        The query will store the results from prior times when we've asked 
        and avoid re-doing queries.   So, if a prior query had asked whether
        ['corn', 'cow', 'carrot'] were vegetables, only 'banana' would be 
        queried and the cached results from the others would be returned.

        Also, if the list contains duplicates, they are removed from the 
        query, and result (you can't have duplicate dict keys).

        This returns a dictionary with a key for each item in listofitems.
        The values are a list of the strings that were returned which mentioned
        that item.  

        I wrote this by hand."""

        retdict = {}

        itemstoquery = listofitems[:]

        # first let's figure out what we actually need to look up...
        for item in listofitems:
            # I'm supposed to ignore the cache, so will re-request.
            if not self.checkcache:
                break

            # if I know it, add it to the return list
            if item in self.cache['list'] and querystring in self.cache['list'][item]:
                itemstoquery.remove(item)
                retdict[item] = self.cache['list'][item][querystring]

        # exit if there is nothing to do...
        if not itemstoquery:
            return retdict

        totalitemstoquery = itemstoquery

        while totalitemstoquery:

            global MAX_ITEMS_PER_QUERY
            # figure out this query and get the next set
            itemstoquery = totalitemstoquery[:MAX_ITEMS_PER_QUERY]
            # remove the items we're about to use...
            totalitemstoquery = totalitemstoquery[MAX_ITEMS_PER_QUERY:]

            # otherwise query!   I'm assuming I can separate things by a comma
            # and a space and this is fine.   I will double quote them so that 
            # this is less ambiguous
            result = self.do_query(querystring+" "+join_with_quotes_and_commas(itemstoquery), optionalprefix)

            for item in itemstoquery:
                # this is really where the magic (and the pain) is at.   This
                # likely will need to be rethought several times...
                thisresult = _do_result_parsing_for_list(item, result)

                # update the cache, if desired...
                if self.updatecache:
                    if item not in self.cache['list']:
                        self.cache['list'][item] = {}

                    self.cache['list'][item][querystring] = thisresult
                    
                retdict[item] = thisresult

            # flush if needed...
            if self.updatecache and self.autoflushcache:
                self.write_cache_to_disk()

        return retdict


    def do_query_which_returns_unambiguous_ordered_list(self, querystring, optionalprefix =''):
        """ Used to do an OpenAI query which returns an ordered list.
        "List the wives of Henry VIII from oldest to youngest at their time of marriage.  Be concise:" returns: "1. Catherine of Aragon
2. Anne Boleyn
3. Jane Seymour
4. Anne of Cleves
5. Catherine Howard
6. Catherine Parr"

        This function will return: ["Catherine of Aragon","Anne Boleyn","Jane Seymour", "Anne of Cleves", "Catherine Howard", "Catherine Parr"]

        This does not handle more complex situations with optional items or 
        things which have "or" / "and" statements!

        ChatGPT helped to write this."""

        input_string = self.do_query(querystring,optionalprefix)

        #### JAC: I asked ChatGPT to write the below code with the doc string
        lines = input_string.strip().split('\n')
        results = []
        seen_numbers = set()

        for line in lines:
            # Split the line into number and content
            if '.' not in line:
                raise ValueError("Each line must be numbered.")

            try:
                number, content = line.split('.', 1)
                # Strip whitespace and check validity
                number = int(number.strip())
                content = content.strip()
            except ValueError:
                raise ValueError(f"Invalid format in line: '{line}'")

            # Check for duplicates and proper ordering
            if number in seen_numbers:
                raise ValueError(f"Duplicate number found: {number}")

            if len(seen_numbers) > 0 and number != max(seen_numbers) + 1:
                raise ValueError("Numbers are not in consecutive order.")

            seen_numbers.add(number)
            results.append(content)

        return results



    def kb_flush(self, shortname=None):
        """Wipes out the knowledgebase under the specified key, or all keys,
        if none is specified.

        I wrote this by hand"""

        if shortname is None:
            self.cache['kb'] = {}
            return

        del self.cache['kb'][shortname]



    def kb_list_update(self, shortname, querystring, query_list = None, forcetype = "any"):
        """Update the knowledge base with the result of a query.   You can 
        update it for all items that have ever been queried, or specify only
        specific items.

        The shortname is the name you want to look up the property under.

        It's also possible to list the type that you wish all items to be 
        converted to.   If this isn't specified, then prefer float over
        int over None (for strings with only whitespace) over strings.
        All items must be able to be converted to the specified type

        Note that the items must be in the cache to start with.

        I wrote this myself."""

        for item in self.cache['list']:
            # if we have a querylist, skip items not in there...
            if query_list is not None and item not in query_list:
                continue
            if querystring in self.cache['list'][item]:
                break
        else:
            raise ValueError("Unknown querystring in kb_list_update: '"+querystring+"'")

        # first get a list of all of the values so we can pass them into our
        # helper function
        resultlist = []
        for item in self.cache['list']:

            # if we have a querylist, skip items not in there...
            if query_list is not None and item not in query_list:
                continue

            if querystring in self.cache['list'][item]:
                assert len(self.cache['list'][item][querystring]) == 1
                resultlist.append(self.cache['list'][item][querystring][0])

        if shortname not in self.cache['kb']:
            self.cache['kb'][shortname] = {}

        # now, stick the keys in the knowledgebase...
        self.cache['kb'][shortname].update(create_uniform_dictionary_from_resultlist(resultlist))




    def kb_list_query(self, shortname, querystring, listofitems, optionalprefix='', forcetype="any"): 
        """ This is a convenience function that does a list query and puts the
        result into the knowledgebase.  It returns the dicutionary from the 
        query, as with do_query_with_list_arguments

        I wrote this by hand"""

        result = self.do_query_with_list_arguments(querystring, listofitems, optionalprefix)
        self.kb_list_update(shortname, querystring, listofitems, forcetype)

        return result




def _do_result_parsing_for_list(target, result):
    """ Looks for a target in the result output.   Can be used to parse
    or re-parse a result for this purpose.

    Philosophically, I could tokenize it with split and then try to find 
    lines that match.   I will do similar, by checking that what comes
    before and after is whitespace.  This may need to be rethought later...
    I will return a list of all lines with the target for now.

    If nothing is found, return []

    I wrote this by hand."""

    resultlist = []
    for line in result.split('\n'):
        # sometimes the quotes are unicode.   Convert them to ascii
        line = line.replace('\u201c','"')
        line = line.replace('\u201d','"')

        if target in line:
            
            if line.count('"') == 0:
                item = line.strip()

            else:
                if line.count('"') != 2:
                    # it is missing the quotes, so skip it...
                    continue

                before, item, after = line.split('"')
                if before != '':
                    # data is before the first double quote...
                    continue

                if item != target:
                    # these are not the droids you're looking for...
                    continue

            # drop the quotes and whitespacm
            resultlist.append(line.strip().replace('"',''))

    return resultlist



def sanitize_list_output(result):
    """ Takes a raw result string which is of a format like:
    - item1
    - item2
    OR
    1. item1
    2. item2
    and returns a list of the strings without the leading numbers or
    dashes."""

    # Split the result into lines
    lines = result.strip().split('\n')

    # Initialize an empty list to hold the sanitized items
    sanitized_items = []

    for line in lines:
        # Remove leading dashes or numbers and strip whitespace
        sanitized_line = line.lstrip('-1234567890.): ').strip()
        if sanitized_line:  # Only add non-empty lines
            sanitized_items.append(sanitized_line)

    return sanitized_items





def split_or_items_in_list(query_list):
    """ Given a list of strings with OR items, split each OR item into a 
    separate list at the same position.

    input_list = ['Alice', 'Bob or Sue or Jane', 'Tom, Dick, or Harry', 'Charlie']
    output = split_or_items_in_list(input_list)
    print(output)  # Output: ['Alice', ['Bob', 'Sue', 'Jane'], ['Tom', 'Dick', 'Harry'], 'Charlie']

    Note, I had ChatGPT generate this.   I checked and it seems to work
    (however things like 'and' likely will break this)."""

    result = []

    for item in query_list:
        # Split the item by commas
        sub_items = [i.strip() for i in item.split(',')]
        split_items = []  # To hold final split items for the current entry

        for sub_item in sub_items:
            # Further split by 'or' and strip leading/trailing whitespace
            or_split = [i.strip() for i in sub_item.split(' or ')]

            for item in or_split[:]:
                # I need this or else "Tom, Dick, or Harry" is split into
                # ['Tom', 'Dick', 'or Harry'].  If I just split on things
                # with 'or ' above, this would incorrectly detect words 
                # ending in or
                if item.startswith('or '):
                    or_split.remove(item)
                    or_split.append(item[len('or '):])
                
            split_items.extend(or_split)  # Extend the list with the split items

        # Append either a list or a single item to the result
        result.append(split_items if len(split_items) > 1 else split_items[0])

    return result


def flatten_and_items_in_list( query_list):
    """ Given a list of strings with AND items, flatten each item into the
    main list in the same position.

    input_list = ['Alice', 'Bob and Sue or Jane', 'Amy, Barb, or Beth', 'Tom, Dick, and Harry', 'Charlie']
    output = flatten_and_items_in_list(input_list)
    print(output)  # Output: ['Alice', 'Bob', 'Sue or Jane', 'Amy, Barb, or Beth', 'Tom', 'Dick', 'Harry', 'Charlie']

    ChatGPT failed to write a version on this which passed the input after
    trying 5 times.   I adapted this from split_or_items_in_list"""

    result = []

    for item in query_list:

        if ' and ' not in item:
            result.append(item)
            continue

        # Split the item by commas
        sub_items = [i.strip() for i in item.split(',')]
        split_items = []  # To hold final split items for the current entry

        for sub_item in sub_items:
            # Further split by 'and' and strip leading/trailing whitespace
            and_split = [i.strip() for i in sub_item.split(' and ')]

            for item in and_split[:]:
                # I need this or else "Tom, Dick, and Harry" is split into
                # ['Tom', 'Dick', 'and Harry'].  If I just split on things
                # with 'or ' above, this would incorrectly detect words
                # ending in or
                if item.startswith('and '):
                    and_split.remove(item)
                    and_split.append(item[len('and '):])

            split_items.extend(and_split)  # Extend the list with the split items

        # Extend the items to the list
        result.extend(split_items)

    return result



def remove_optional_items_in_list(query_list, omitstring='(optional)'):
    """ Given a list of strings, remove any item with (optional) in it.
    separate list at the same position.

    input_list = ['Alice', 'Bob (optional)', 'Tom', 'Charlie (optional)']
    output = remove_optional_items_in_list(input_list):
    print(output)  # Output: ['Alice', 'Tom']"""

    return [item for item in query_list if item.find(omitstring)==-1]






### The code below here was ChatGPT written (mostly).   I changed the code a 
### bit because it wasn't handling "None" values as I intended.   In the end,
### I decided to change my design instead of changing the code more heavily.
### So, I shaped my design to better match the results ChatGPT gave me (after 
### fixing a bug).   I'm not sure how I feel about this.   
def _convert_value(val):
    """Attempt to convert the value to int or float with a fallback to string."""
    try:
        return int(val)  # Attempt to convert to integer
    except ValueError:
        try:
            return float(val)  # Attempt to convert to float
        except ValueError:
            if val == "True":
                return True
            elif val == "False":
                return False
            else:
                return val  # If all else fails, leave as string

def _uniform_type_cast(values):
    """Ensure that all values in the list are of the same type."""
    # Check if all values are boolean.  I must do this first, since bools are
    # ints (for some crazy reason)
    if all(isinstance(v, bool) for v in values):
        return list(map(bool, values))

    # Check if all values are int
    if all(isinstance(v, int) for v in values):
        return list(map(int, values))

    # Check if all values can be converted to float
    if all(isinstance(v, (int, float)) for v in values):
        return list(map(float, values))


    # If neither, return everything as a series of strings
    return list(map(str, values))



def create_uniform_dictionary_from_resultlist(lst):
    """Convert a list of strings into a dictionary with uniform value data types."""
    result = {}

    for item in lst:
        parts = item.split(' ', 1)  # Split into main word and remaining info
        key = parts[0]
        value = _convert_value(parts[1].strip()) if len(parts) > 1 else ""
        result[key] = value

    # Get all values and attempt to cast them to a uniform type
    values = list(result.values())
    uniform_values = _uniform_type_cast(values)

    # Rebuild the dictionary with uniform type values
    result = dict(zip(result.keys(), uniform_values))

    return result
