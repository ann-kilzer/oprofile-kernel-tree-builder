#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
"""Oprofile Kernel Tree Builder: a script for analyzing the oprofile output.

This version does not generate the ctags file, though I have included a bash
script that does.  I am also working on a python script to generate ctags.
The oprofile output and the ctags file must be passed via the command line as
shown:

  $ python treeprint.py -f <oprofile output> -t <ctags file> -p <path to kernel> [-b bound]

The bound is optional.  The rest of the parameters are required.

The script looks through the oprofile output and builds a dictionary containing
the function names and the percentage of cpu cycles used by each.  It then
searches for the function names in the ctags output in order to determine the
location of each function inside the kernel.  Finally, the program creates a
tree representing the directory structure of the kernel.  Each node represents a
directory, file, or function, and contains the associated cpu percentage.

The program outputs a long list of nodes from each level of the tree and their
associated cpu percentages.  This uses a level order traversal sequence.  A
later version may incorporate a graphical output.

  OprofileInfo: Builds a dictionary from the Oprofile output.
  DirTree: directory-like tree containing information about the directory
           hierarchy and associated cpu percentage.
  Node: subclass of DirTree: each Node represents a directory, file, or
function.
"""

__author__ = 'akilzer@gmail.com (Ann Kilzer)'

from optparse import OptionParser


class OProfileInfo(object):

  """Data from oprofile output in a dictionary.

  Parses oprofile output and stores symbol name and % cpu cycles
  in a dictionary called fcns.

  Attributes:
    fcns: A dictionary keyed on symbol name containing a subdictionary
          with float values of % cpu cycles and the app name.
  """

  def __init__(self, filename):
    """Inits OprofileInfo and calls __Parse, building dictionary.

    Args:
      filename: A filename containing output from oprofile.
    """
    self.fcns = {}
    self._Parse(filename)

  def _Parse(self, filename):
    """Parse samples, % cpu and symbol name and builds a dictionary.

    Args:
      filename: A filename containing output from oprofile.

    Raises:
      IOError: an error occured reading the file
    """
    ofile = None
    try:
      for ofile in open(filename).readlines()[3:]:
        line = ofile.rstrip().split(None, 4)
        if len(line) != 5:
          break
        cpu = float(line[1]) + self.fcns.get(line[4], {'cpu%': 0.0})['cpu%']
        self.fcns[line[4]] = {'cpu%': cpu, 'appname': line[3]}
    except IOError, e:
      print e

  def IsEmpty(self):
    """Returns true if function list fcns is empty."""
    return not self.fcns


class DirTree(object):

  """Directory tree with info on cpu usage from oprofile output.

  Each node represents a directory, file, or function, and contains
  the percentage of cpu cycles belonging to the directory, file, or function.

  Attributes:
    root: The root Node represents the root of the kernel and has name '/'.
    print_tree: A dictionary keyed on tree level containing node information
       for each level.  This is used for printing the tree.
  """

  class Node(object):

    """Represents each node (directory, file, or function) in the DirTree.

    Attributes:
      name: The name of directory/file/function.
      percent: A float representing % of cpu cycles belonging to node.
      type: Either 'dir', 'file', or 'fcn'.
      children: A dictionary keyed on names of children with pointers to the
           child nodes.
    """

    def __init__(self, node_name, node_path, node_type, node_app=None):
      """Initialization of Node object.

      Args:
        node_name: A string representing the name of the directory/file/
            function.
        node_path: A string representing the filesystem path for this node.
        node_type: A string that is either 'dir', 'file', or 'fcn'.
        node_app: A string representing the fourth column of oprofile output,
            indicating whether the symbol is part of kernel, library, etc.
      """
      self.name = node_name
      self.children = {}
      self.percent = 0.0
      self.path = node_path
      self.type = node_type
      self.appname = node_app

    def IsFcn(self):
      """Returns true if the Node represents a function."""
      return self.type == 'fcn'

    def IsDir(self):
      """Returns true if the Node represents a directory."""
      return self.type == 'dir'

    def IsFile(self):
      """Returns true if the Node represents a file."""
      return self.type == 'file'

  def __init__(self):
    """Inits DirTree with root node and print_tree dictionary."""
    self.root = self.Node('/', '/', 'dir')
    self.print_tree = {}

  def _InsertHelper(self, node, item, index, path_str):
    """Recursive helper for __insert__.

    Args:
      node: The current node pointed to by this recursive case.
      item: A dictionary with keys cpu% and path, corresponding to values of
          a float and a list of the directory hierarchy.
      index: An integer value representing the offset into the item's 'path'
          dictionary.  Another way to look at this is as the current level
          in the directory hierarchy.
      path_str: A string representing the filesystem path for this node.
    """
    node.percent += item[1]['cpu%']
    if index < len(item[1]['path']):  #do recursive step
      next = item[1]['path'][index]
      appname = item[1]['appname']
      if node.IsFile():
        next_path = '%s: %s' % (path_str, next)
      else:
        next_path = '%s/%s' % (path_str, next)

      if next not in node.children:
        if index == len(item[1]['path']) - 1:
          node.children[next] = DirTree.Node(next, next_path, 'fcn', appname)
        elif index == len(item[1]['path']) - 2:
          node.children[next] = DirTree.Node(next, next_path, 'file')
        else:
          node.children[next] = DirTree.Node(next, next_path, 'dir')
      self._InsertHelper(node.children[next], item, index + 1, next_path)

  def Insert(self, item):
    """Inserts item (representing a directory, file, or function) into DirTree.

    Args:
      item: a dictionary with keys cpu% and path, corresponding to values of
      a float and a list of the directory hierarchy.
    """
    if len(item[1]['path']) > 0:
      self._InsertHelper(self.root, item, 0, '')

  def _PrintHelper(self, node, level, parent_str):
    """Recursive helper for __PrintMe__.

    Args:
      node: The current node pointed to by this recursive case.
      level: The level of the directory tree we're on, starting with 0 for root.
      parent_str: A string representing the filesystem path to the directory/
          file/function.
    """
    if not level in self.print_tree:
      self.print_tree[level] = []
    if level == 1:
      parent_str = '/'
    parent_str += '%s' % node.name
    self.print_tree[level].append('%s:  %.2f' % (parent_str, node.percent))

    temp = [(child.percent, child) for child in node.children.itervalues()]
    temp.sort()
    temp.reverse()
    for percent, child in temp:
      self._PrintHelper(child, level + 1, parent_str +
                        (child.IsFcn() and ':  ' or '/'))

  def PrintMe(self):
    """Prints out DirTree by level, sorted by % cpu cycles.

    This uses a level order traversal for printing out the nodes.  The
    output will be sorted at levels 0 and 1.  For remaining levels, the output
    will be sorted by the % cpu cycles of the parent, and further sorted by the
    % cpu cycles of the child.  These are the characteristics of the level
    order traversal.
    """
    if not self.root.children:
      print 'Empty Tree'
    else:
      self._PrintHelper(self.root, 0, '')

      for level, data in self.print_tree.items():
        print '*' * 50
        print 'Level %d:' % level
        for item in data:
          print item

  def PrintMe2(self, threshold=0):
    """Prints out DirTree by level, sorted by % cpu cycles.

    This uses a breadth first traversal and is more elegant, requiring only
    one traversal.

    Args:
      threshold: A lower bound on the % of cpu cycles.  Items with % cpu
      cycles below the threshold will not be printed.  This is useful for
      making the output more readable.
    """
    print '*' * 50
    last_line_node = False
    if not self.root.children:
      print 'Empty Tree'
    else:
      queue = []
      queue.append(self.root)
      queue.append('*' * 50)

      while queue:
        #dequeue
        cur = queue.pop(0)
        try:
          if cur.percent > threshold:
            print '%s: %.4f' % (cur.path, cur.percent)
            last_line_node = True
          #append children
          temp = [(child.percent, child) for child in cur.children.itervalues()]
          temp.sort()
          temp.reverse()
          for percent, child in temp:
            queue.append(child)
          if temp:
            queue.append('*' * 50)
        except AttributeError:
          # This is a string
          if last_line_node:
            print cur
            last_line_node = False


def GetCtags(filename, path):
  """Reads ctags file and creates a dictionary.

  Arguments:
    filename: The ctags output.
    path: The path to the kernel sources listed in the ctags.  This will
          be stripped from the ctags strings.
  Returns:
    A dictionary keyed on symbol name containing the filesystem path
    to the symbol.  The path is contained in a list.
  Raises:
    IOError: an error occured reading the file
  """
  tag_dict = {}
  try:
    for cfile in open(filename):
      line = cfile.split(None, 2)
      if len(line) != 3:
        break
      tag_dict[line[0]] = line[1][len(path):]
      # flag: be sure to enter the correct path!
  except IOError, e:
    print e
  return tag_dict


def PrintLostItems(lost_items):
  """Writes lost items to outfile and calculates % of lost cycles.

  This is a helper function for FindItems that deals with the lost items:
  items which have not been paired with ctags items.  The names of these
  items are printed to lostitems.txt.
  Args:
    lost_items: A dictionary of lost items from the FindItems function.
  """
  sum_cpu = 0.0
  lost_file = open('lostitems.txt', 'w')
  temp = [(i.get('cpu%', 0.0), name) for (name, i) in lost_items.items()]
  temp.sort()
  temp.reverse()
  for (cpu, name) in temp:
    sum_cpu += cpu
    print >>lost_file, '%s: %.4f' % (name, cpu)
  lost_file.close()
  print 'lost items account for %.2f %% of cycles' % sum_cpu


def FindItems(oprof, ctags):
  """Makes a list of items with function name, % cpu, and location.

  Args:
    oprof: OProfileInfo object.
    ctags: Dictionary returned by GetCtags.

  Returns:
    A list of found items: a dictionary keyed on symbol name containing
    sub-dictionaries with % cpu cycles and a list represeting the filesystem
    path.
  """
  found_items = {}
  lost_items = {}

  for fcn_name in oprof.fcns:
    loc = ctags.get(fcn_name, None)
    fcn_data = {}
    fcn_data['cpu%'] = oprof.fcns[fcn_name]['cpu%']
    fcn_data['appname'] = oprof.fcns[fcn_name]['appname']
    if not loc:
      lost_items[fcn_name] = fcn_data
    else:
      fcn_data['path'] = loc.lstrip('./').split('/')
      fcn_data['path'].append(fcn_name)
      found_items[fcn_name] = fcn_data

  print 'found items: %d' % len(found_items)
  print 'lost items: %d' % len(lost_items)
  PrintLostItems(lost_items)
  return found_items

if __name__ == '__main__':
  parser = OptionParser()
  parser.add_option('-p', '--path', dest='path',
                    help='path to kernel', metavar='PATH')
  parser.add_option('-f', '--file', dest='filename',
                    help='oprofile input file', metavar='FILE')
  parser.add_option('-t', '--tags', dest='tags', help='ctags input file',
                    metavar='FILE')
  parser.add_option('-b', '--bound', dest='bound', help='lower bound')
  (options, args) = parser.parse_args()

  if not options.filename:
    print 'Error: Need to specify filename (-f)'
  elif not options.path:
    print 'Error: Need to specify path (-p)'
  elif not options.tags:
    print 'Error: Need to specify tags (-t)'
  else:
    try:
      thresh = float(options.bound)
    except ValueError:
      print 'Error in setting bound.  Using 0.0 for bound.'
      thresh = 0.0
    if thresh < 0.0 or thresh > 100.0:
      print 'Error: Bound must be between 0.0 and 100.0.  Using 0.0 for bound.'
      thresh = 0.0

    oprof = OProfileInfo(options.filename)
    print 'total items: %d' % len(oprof.fcns)
    ctags = GetCtags(options.tags, options.path)
    if ctags and not oprof.IsEmpty():
      found_items = FindItems(oprof, ctags)
      tree = DirTree()
      for item in found_items.items():
        tree.Insert(item)

      tree.PrintMe2(thresh)
