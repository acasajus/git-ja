#!/usr/bin/env python

import argparse
import sys
import inspect
import subprocess
import logging


class ColoredStreamHandler( logging.StreamHandler ):

  colorIndex = ( 'black', 'red', 'green', 'orange', 'blue', 'violet', 'lightblue', 'gray', 'darkgray', 'inv' )
  colorMap = { logging.DEBUG : 'lightblue', logging.INFO : False, logging.WARNING : 'gray',
               logging.ERROR : 'red', logging.FATAL : 'orange' }

  @property
  def isTTY( self ):
    istty = getattr( self.stream, 'isatty', None )
    return istty and istty()

  def emit( self, record ):
    try:
      message = self.format( record )
      if self.isTTY:
        message = self.colorize( record.levelno, message )
      self.stream.write( message )
      self.stream.write( getattr( self, 'terminator', '\n' ) )
      self.flush()
    except ( KeyboardInterrupt, SystemExit ):
      raise
    except:
      self.handleError( record )

  def colorize( self, lvl, msg ):
    c = self.colorMap[ lvl ]
    if not c:
      return msg
    iC = max( 0, self.colorIndex.index( c ) )
    return "\033[;3%dm%s\033[0m" % ( iC, msg )

log = logging.getLogger( __name__ )
log.addHandler( ColoredStreamHandler() )
log.setLevel( logging.INFO )

class Command( object ):

  def __init__( self, parser ):
    self.parser = parser
    self.maniac = False
    self.parser.description = self.description()
    self.parser.usage = "git-ja {} [opts]".format( self.name() )

  @classmethod
  def name( cls ):
    return cls.__name__.lower()

  @classmethod
  def description( cls ):
    return "FILL THIS YOU LAZY DOG"

  def arm( self ):
    pass

  def fire( self ):
    self.opts = self.parser.parse_args( sys.argv[2:] )
    if self.opts.debug:
      log.setLevel( logging.DEBUG )
    self.maniac = self.opts.maniac
    if self.maniac:
      log.debug( "MANIAC mode on" )
    return self.work( self.opts )

  def run( self, cmd, checkValid = False ):
    log.debug( "Exec %s" % cmd )
    sp = subprocess.Popen( cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE )
    data = ""
    stepRead = 8192
    while True:
      buf = sp.stdout.read( stepRead )
      if buf:
        data += buf.decode('utf-8')
      if len( buf ) < stepRead:
        break
    wait = sp.wait()
    if wait != 0:
      err = sp.stderr.read()
      if not err:
        err = data
      if checkValid:
        return False
      log.error( "While executing [%s]:\n%s" % ( cmd, err ) )
      sys.exit( wait )
    if checkValid:
      return True
    sp.stderr.close()
    sp.stdout.close()
    return data.strip()

  def gitCurrentBranch( self ):
    return self.run( "git rev-parse --abbrev-ref HEAD" )

  def gitLocalBranches( self ):
    return set( ( line.split( "/" )[-1] for line in self.run( "git show-ref --heads" ).split( '\n' ) ) )

  def gitRemoteBranches( self ):
    if self.maniac:
      log.info( "Getting information from remotes" )
      self.run( "git fetch --all --prune" )

    data = self.run( "git show-branch --remotes --list" )
    return set( ( l[ l.find( "[" ) + 1: l.find( "]" ) ] for l in data.split( "\n" ) ) )

  def gitTracking( self, branch = False ):

    if branch:
      ref = "refs/heads/" + branch
    else:
      ref = "refs/heads"

    rembranches = self.gitRemoteBranches()

    data = {}
    for line in self.run( "git for-each-ref --format='%(refname:short) %(upstream:short)' " + ref ).split( "\n" ):
      l = line.split()
      if len( l ) == 2:
        lb = l[0]
        rb = l[1]
        if rb in rembranches:
          data[ lb ] = rb
        elif self.maniac:
          log.info( "Cleaning inexistant {} upstream for branch {}".format( rb, lb ) )
          self.run( "git branch --unset-upstream {}".format( lb ) )
        else:
          log.debug( "{} tracks {} that does not exist any more".format( lb, rb ) )
    return data


class Promote( Command ):

  @classmethod
  def description( cls ):
    return "Send branch to remote"

  def arm( self ):
    self.parser.add_argument( "-r", "--remote", action = 'store', default = False, help = 'Promote to this remote' )
    self.parser.add_argument( "-x", "--remote-branch", dest = 'remoteBranch', action = 'store', default = False, help = 'Remote branch to promote to' )
    self.parser.add_argument( "-u", "--upstream", action = 'store_true', default = False, help = 'Set upstream for git push/pull' )
    self.parser.add_argument( 'branches', metavar = 'branches', nargs = argparse.REMAINDER, help = "Branches to promote" )

  def work( self, opts ):
    if opts.upstream:
      basecmd = "git push -u"
    else:
      basecmd = "git push"
    branches = opts.branches
    if not branches:
      branches = [ self.gitCurrentBranch() ]
    for branch in branches:
      rembranch = opts.remoteBranch
      remname = opts.remote
      if not remname:
        data = self.gitTracking( branch )
        data = data.get( branch, 'origin/{}'.format( branch ) ).split( "/" )
        remname = data[0]
        if not rembranch:
          rembranch = data[1]
      if not rembranch:
        rembranch = branch
      log.info( "Promoting {} to {}/{}".format( branch, remname, rembranch ) )
      if not self.run( "{} {} {}:{}".format( basecmd, remname, branch, rembranch ) ):
          return False
    log.info( "Done" )
    return True

class ShowTracking( Command ):

  @classmethod
  def name( cls ):
    return 'show-tracking'

  @classmethod
  def description( cls ):
    return "Show tracking branches"

  def arm( self ):
    self.parser.add_argument( "-c", "--current", action = 'store_true', default = False, help = 'Mark the current branch' )

  def work( self, opts ):
    data = self.gitTracking()
    log.debug( "Showing tracking branches" )
    ml = max( ( len(k) for k in data ) )
    if opts.current:
      cb = self.gitCurrentBranch()
    for k in data:
      t = data[k]
      if opts.current:
        ward = '- '
        if l[0] == cb:
          ward = '+ '
      else:
        ward = ''
      log.info( "{}{} : {}".format( ward, k, t.rjust( ml ) ) )
    return True

class Divergence( Command ):

  @classmethod
  def description( cls ):
    return "Graph divergence tree between branches"

  def arm( self ):
    self.parser.add_argument( '-r', '--include-upstream', dest = 'includeUpstream', 
                              action = 'store_true', default = False, help = 'Include upstream branches for divergence tree' )
    self.parser.add_argument( '-t', '--topo-order', dest = 'topoOrder', 
                              action = 'store_true', default = False, help = 'Show tree in topological order instead of date ordered' )
    self.parser.add_argument( 'refs', nargs = '*', help = 'Branches used to calculate the divergence graph' )

  def work( self, opts ):
    refs = opts.refs
    if not refs:
      refs = self.gitLocalBranches()
    if opts.includeUpstream:
      track = self.gitTracking()
      refs.extend( [ track[k] for k in refs if k in track ] )
    if len( refs ) < 2:
      log.error( "Not enough references to generate tree" )
      return False
    log.info( "Generating divergence between " + " ".join( refs ) )
    base = self.run( "git merge-base --octopus " + " ".join( refs ) ).strip()
    if not base:
      return False
    name = self.run( "git name-rev {}".format( base ) ).strip().split()[1]
    if name.find( "remotes/" ) == 0:
      name = name[ 8: ]
    log.info( "Graph origin is {}".format( name ) )
    try:
      refs.remove( name )
    except ValueError:
      pass
    order = 'topo' if opts.topoOrder else 'date'
    cmd = "git log --{}-order --graph --color --pretty=format:%x1b[31m%h%x09%x1b[32m%d%x1b[0m%x20%s {}^! {}".format( order, base, " ".join( refs ) )
    log.info( self.run( cmd ) )
    return True

class Vanish( Command ):

  @classmethod
  def description( cls ):
    return "Remove branches locally and from upstream"

  def arm( self ):
    self.parser.add_argument( "-r", "--remote", action = 'store', default = False, help = 'Remove from this remote' )
    self.parser.add_argument( "-f", "--force", action = 'store_true', default = False, help = 'Force branch deletion' )
    self.parser.add_argument( 'branches', metavar = 'branches', nargs = argparse.REMAINDER, help = "Branches to promote" )

  def work( self, opts ):
    switch = '-d'
    if opts.force:
      switch = '-D'
    branches = opts.branches
    if not branches:
      log.error( "Which branches do you want to remove?" )
      sys.exit(1)
    for branch in branches:
      rembranch = ""
      remname = opts.remote
      if not remname:
        data = self.gitTracking( branch )
        data = data.get( branch, 'origin/{}'.format( branch ) ).split( "/" )
        remname = data[0]
        rembranch = data[1]
      if not rembranch:
        rembranch = branch
      log.info( "Removing {} and {}/{}".format( branch, remname, rembranch ) )
      if not self.run( "git branch {} {}".format( switch, branch ) ):
          return False
      if not self.run( "git push {} :{}".format( remname, rembranch ) ):
          return False
    log.info( "Done" )
    return True

class GitJa( object ):

  def __init__( self ):
    self.__cmds = dict( [ ( cls.name(), cls ) for cls in Command.__subclasses__() ] )
    mx = max( [ len( k ) for k in self.__cmds ] )

    usecmd = "\n  ".join( [ "{}: {}".format( k.rjust( mx ), self.__cmds[k].description() ) for k in self.__cmds ] )
    usage = "git-ja command [opts]\n\nAvailable commands:\n  {}".format( usecmd )

    self.__parser = argparse.ArgumentParser( description = "Git-ja utilities for gitjas!",
                                           usage = usage,
                                           formatter_class = argparse.RawDescriptionHelpFormatter )
    self.__parser.add_argument( '-d', '--debug', action = 'store_true', default = False, help = "Enable debug output" )
    self.__parser.add_argument( '-m', '--maniac', action = 'store_true', default = False, help = "Update any required information" )

  def __searchCommand( self ):
    if len( sys.argv ) < 2:
      log.error( "Missing command" )
      return False
    q = sys.argv[1]
    if q in self.__cmds:
      return self.__cmds[q]
    cmds = [ k for k in self.__cmds ]
    for iP in range( len( q ) ):
      c = q[iP]
      cmds = [ k for k in cmds if len( k ) > iP and k[iP] == c ]
      if len( cmds ) == 1:
        return self.__cmds[ cmds[ 0 ] ]
    if len( cmds ) > 1:
      log.error( "Ambiguous command. Which one of {} is it?".format( cmds ) )
      return False
    log.error( "Unknown command" )
    return False

  def act( self ):
    cmdClass = self.__searchCommand()
    if not cmdClass:
      self.__parser.print_help()
      return False
    cmd = cmdClass( self.__parser )
    cmd.arm()
    return cmd.fire()

def run():
  gitja = GitJa()
  if gitja.act():
    sys.exit(0)
  else:
    sys.exit(1)

if __name__ == "__main__":
  run()

