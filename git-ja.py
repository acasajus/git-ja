#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re

parser = argparse.ArgumentParser( description = "Git remote manager" )
parser.add_argument( '-d', '--debug', action = 'store_true', help = "Enable debug output" )
parser.add_argument( '-l', '--list', action = 'store_true', help = "List all remotes" )
parser.add_argument( '-u', '--update', action = 'store_true', help = "Update all remotes" )
parser.add_argument( '-t', '--status', action = 'store_true', help = "Show status of all branches with remotes" )
parser.add_argument( '-i', '--divergence', action = 'store_true', help = "Show divergence tree of given commits" )
parser.add_argument( '-a', '--aheadlog', action = 'store_true', help = "Retrieve a list of commits ahead of tracked remote branch" )
parser.add_argument( '-s', '--shy', action = 'store_true', help = "Do not execute any remote query" )
parser.add_argument( 'commits', metavar='commit', nargs='*' )
doneStuff = False
parseRes = parser.parse_args()


def debug( msg ):
  if parseRes.debug:
    print "[DEBUG] %s" %msg

def magicSplit( data, char = None ):
  return [ f.strip() for f in data.split( char ) if f.strip() ]
 
def getBranchTacks( head ):
  remote = do( "git config branch.%s.remote" % head )
  merge = "/".join( do( "git config branch.%s.merge" % head ).split( "/" )[2:] )
  return "%s/%s" % ( remote, merge )

def exists( commit ):
  return do( "git log -n 1 --pretty=oneline %s" % commit, checkValid = True )

  
def getCommits( defaultAll = True, insertTrackedIfOne = False ):
  for commit in parseRes.commits:
    if not exists( commit ):
      print "Commit %s doesn't seem to be valid" % commit
      sys.exit(1)
  if parseRes.commits:
    commits = parseRes.commits
  elif defaultAll:
    commits = [ com.lstrip( '*' ).strip() for com in do( "git br" ).split( "\n" ) if com.strip() ]
  else:
    commits = [ com.lstrip( '*' ).strip() for com in do( "git br" ).split( "\n" ) if com.strip().find( "*" ) == 0 ]
  if len( commits ) and insertTrackedIfOne:
    commits.insert( 0, getBranchTacks( commits[0] ) )
  return commits
      

def getCommit( head ):
  return do( "git log -n 1 --pretty=format:%%H %s" % head )
 
def do( cmd, checkValid = False ):
  debug( "Exec %s" % cmd )
  sp = subprocess.Popen( cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
  data = ""
  stepRead = 8192
  while True:
    buf = sp.stdout.read( stepRead )
    if buf:
      data += buf
    if len( buf ) < stepRead:
      break
  wait = sp.wait()
  if wait != 0:
    err = sp.stderr.read()
    if not err:
      err = data
    if checkValid:
      return False
    print "ERROR while executing [%s]:\n%s" % ( cmd, err )
    sys.exit( wait )
  if checkValid:
    return True
  sp.stderr.close()
  sp.stdout.close()
  return data.rstrip()

if parseRes.list:
  doneStuff = True
  remotes = magicSplit( do( "git remote show" ) )
  print "%s remotes: %s" % ( len( remotes ), ", ".join( remotes ) )
  for remote in remotes:
    cmd = "git remote show %s" % remote
    if parseRes.shy:
      cmd += " -n"
    print do( cmd )
if parseRes.update:
  doneStuff = True
  print "Updating remotes..."
  print do( "git remote update --prune" )
  
## Divergence
if parseRes.divergence:
  doneStuff = True
  commits = getCommits( insertTrackedIfOne = True )
  mergeBase = do( "git merge-base --octopus %s" % " ".join( commits ) )
  if not commits:
    commits = [ "HEAD" ]
  iP = 0
  while iP < len( commits ):
    if mergeBase == getCommit( commits[iP] ):
      mergeBase = commits[iP]
      commits.pop( iP )
    iP += 1
  if not commits:
    print "There is no history betweed defined commits"
  else:
    cmd = "git log --graph --color --boundary --pretty=format:%s %s..%s" % ( "%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s", mergeBase, " ".join( commits ) )
    print do( cmd )

## Commlog

if parseRes.aheadlog:
  doneStuff = True
  remlog = re.compile( "^ *\*? +([\-\w]+) +\w+ +\[(ahead|behind) +([0-9]+)\].*$" )
  commits = getCommits( defaultAll = False )
  found = {}
  for line in do( "git branch -v" ).split( "\n" ):
    match = remlog.match( line )
    if match:
      groups = match.groups()
      if groups[0] in commits:
	found[ groups[0] ] = ( groups[1], int( groups[2] ) )
  for commit in commits:
    if commit not in found:
      continue
    trackedBranch = getBranchTacks( commit )
    if found[ commit ][0] == 'ahead':
      print "\033[;35m*\033[0m %s is \033[;35mAHEAD\033[0m of %s by %d commits:\n" % ( commit, trackedBranch, found[ commit ][1] )
      sTo = ( getBranchTacks( commit ), commit )
    else:
      print "\033[;35m*\033[0m %s is \033[;35mBEHIND\033[0m of %s by %d commits:\n" % ( commit, trackedBranch, found[ commit ][1] )
      sTo = ( commit, getBranchTacks( commit ) )
    print "%s\n" % do( "git log --color '--pretty=format:%%Cgreen%%H %%Cblue%%d%%Creset%%n%%B' %s..%s" % sTo )


if not doneStuff:
  parser.print_help()
  sys.exit( 1 )
