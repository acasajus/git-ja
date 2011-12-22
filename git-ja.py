#!/usr/bin/env python

import argparse
import sys
import subprocess
import os
import re

parser = argparse.ArgumentParser( description = "Git-ja utilities for gitjas!" )
parser.add_argument( '-d', '--debug', action = 'store_true', help = "Enable debug output" )
parser.add_argument( '-r', '--remotes', action = 'store_true', help = "List all remotes" )
parser.add_argument( '-u', '--update', action = 'store_true', help = "Update info about all remotes" )
parser.add_argument( '-t', '--status', action = 'store_true', help = "Show status of all branches with remotes" )
parser.add_argument( '-i', '--divergence', action = 'store_true', help = "Show divergence tree of given refs" )
parser.add_argument( '-f', '--syncLog', action = 'store_true', help = "Get the commits that differ between local and tracked branches" )
parser.add_argument( '-P', '--prune', action = 'store_true', help = "Prune remote branches. If no remote branches are given, origin branches that doesn't exist locally will be used" )
parser.add_argument( '-s', '--shy', action = 'store_true', help = "Do not execute any remote query" )
parser.add_argument( 'refs', metavar='ref', nargs='*' )
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

def exists( ref ):
  return do( "git log -n 1 --pretty=oneline %s" % ref, checkValid = True )

  
def getRefs( defaultAll = False, defaultCurrent = False, insertTrackedIfOne = False ):
  for ref in parseRes.refs:
    if not exists( ref ):
      print "Ref %s doesn't seem to be valid" % ref
      sys.exit(1)
  if parseRes.refs:
    refs = parseRes.refs
  elif defaultAll:
    refs = [ com.lstrip( '*' ).strip() for com in do( "git br" ).split( "\n" ) if com.strip() ]
  elif defaultCurrent:
    refs = [ com.lstrip( '*' ).strip() for com in do( "git br" ).split( "\n" ) if com.strip().find( "*" ) == 0 ]
  else:
    refs = []
  if len( refs ) and insertTrackedIfOne:
    refs.insert( 0, getBranchTacks( refs[0] ) )
  return refs
      

def getRef( head ):
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

#Actual stuff
  
def execRemotes():
  remotes = magicSplit( do( "git remote show" ) )
  print "%s remotes: %s" % ( len( remotes ), ", ".join( remotes ) )
  for remote in remotes:
    cmd = "git remote show %s" % remote
    if parseRes.shy:
      cmd += " -n"
    print do( cmd )

def execUpdate():
  print "Updating remotes..."
  print do( "git remote update --prune" )
  
def execDivergence():
  refs = getRefs( defaultAll = True, insertTrackedIfOne = True )
  mergeBase = do( "git merge-base --octopus %s" % " ".join( refs ) )
  if not refs:
    refs = [ "HEAD" ]
  iP = 0
  while iP < len( refs ):
    if mergeBase == getRef( refs[iP] ):
      mergeBase = refs[iP]
      refs.pop( iP )
      break
  if not refs:
    print "There is no history betweed defined refs"
  else:
    cmd = "git log --graph --color --boundary --pretty=format:%s %s..%s" % ( "%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s", mergeBase, " ".join( refs ) )
    print do( cmd )

def execSyncLog():
  remlog = re.compile( "^ *\*? +([\-\w]+) +\w+ +\[(ahead|behind) +([0-9]+)\].*$" )
  refs = getRefs( defaultCurrent = True )
  found = {}
  for line in do( "git branch -v" ).split( "\n" ):
    match = remlog.match( line )
    if match:
      groups = match.groups()
      if groups[0] in refs:
        found[ groups[0] ] = ( groups[1], int( groups[2] ) )
  for ref in refs:
    if ref not in found:
      continue
    trackedBranch = getBranchTacks( ref )
    if found[ ref ][0] == 'ahead':
      print "\033[;35m*\033[0m %s is \033[;35mAHEAD\033[0m of %s by %d refs:\n" % ( ref, trackedBranch, found[ ref ][1] )
      sTo = ( getBranchTacks( ref ), ref )
    else:
      print "\033[;35m*\033[0m %s is \033[;35mBEHIND\033[0m of %s by %d refs:\n" % ( ref, trackedBranch, found[ ref ][1] )
      sTo = ( ref, getBranchTacks( ref ) )
    print "%s\n" % do( "git log --color '--pretty=format:%%Cgreen%%H %%Cblue%%d%%Creset%%n%%B' %s..%s" % sTo )


    
def execPrune():
  if not parseRes.shy:
    execUpdate()
  refsToDelete = getRefs()
  remoteBranches = []
  for branch in do( "git branch -r" ).split( "\n" ):
    branch = branch.strip()
    if branch.find( "origin/HEAD" ) == -1:
      remoteBranches.append( branch )
  auto = False
  if refsToDelete:
    for ref in refsToDelete:
      if ref not in remoteBranches:
        print "%s is not a remote branch" % ref
        sys.exit(1)
  else:
    auto = True
    for branch in remoteBranches:
      if branch.find( "origin/" ) == 0:
        refsToDelete.append( branch )
  if auto:
    iP = 0
    while iP < len( refsToDelete ):
      branch = refsToDelete[iP].split( "/" )[1]
      if exists( branch ):
        refsToDelete.pop( iP )
      elif raw_input( "%s does not exist locally. Prune? [Y/n]> " % branch ).lower() not in ( 'y', 'yes' ):
        refsToDelete.pop( iP )
      else:
        iP += 1
  if not refsToDelete:
    print "No remote branches found to be pruned"
  else:
    if raw_input( "About to prune %s. Is it OK? [Y/n]> " % ", ".join( refsToDelete ) ).lower() not in ( 'y', 'yes' ):
      print "Prune aborted"
    else:
      for ref in refsToDelete:
        print "Pruning %s" % ref
        if parseRes.shy:
          print "Skipping prune due to shy command"
        else:
          do( "git push %s :%s" % tuple( ref.split( "/" ) ) )

  
#Glue code
  
if parseRes.remotes:
  doneStuff = True
  execRemotes()
if parseRes.update:
  doneStuff = True
  execUpdate()
if parseRes.divergence:
  doneStuff = True
  execDivergence()
if parseRes.syncLog:
  doneStuff = True
  execSyncLog() 
if parseRes.prune:
  doneStuff = True
  execPrune()
    
if not doneStuff:
  parser.print_help()
  sys.exit( 1 )
