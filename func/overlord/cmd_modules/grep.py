"""
grep utility

Copyright 2007, Red Hat, Inc
see AUTHORS

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""


import pprint
import sys
import types

from func.overlord import client
from func.overlord import base_command

class Grep(base_command.BaseCommand):
    name = "grep"
    usage = "grep [--modules = 'module1,module2'] search_term"
    summary = "Greps for some keyword in modules useful for troubleshooting"
    
    def addOptions(self):
        """
        Add options for grep utility ...
        """
        self.parser.add_option("-v", "--verbose", dest="verbose",
                               default=self.verbose,
                               action="store_true")
        self.parser.add_option("-a", "--async", dest="async",
                               help="Use async calls?  (default 0)",
                               default=self.async,
                               action="store_true")
        self.parser.add_option('-d', '--delegate', dest="delegate",
                               help="use delegation to make function call",
                               default=self.delegate,
                               action="store_true")
        self.parser.add_option('-m', '--modules', dest="modules",
                               help="modules to be searched",
                               default=[],
                               action="append")
        
              
    def handleOptions(self, options):
        self.options = options
        self.verbose = options.verbose
        
        # I'm not really a fan of the "module methodname" approach
        # but we'll keep it for now -akl

    def parse(self, argv):
        self.argv = argv
        return base_command.BaseCommand.parse(self, argv)
        

    
    def do(self, args):
        """
        Grepping the stuf real part
        """
        
        if not args:
            self.outputUsage()
            return
        
        #the search keyword
        self.word = args[0]
        
        self.async = self.options.async
        self.delegate = self.options.delegate
        
        self.server_spec = self.parentCommand.server_spec
        self.getOverlord()

        host_modules = self._get_host_grep_modules(self.server_spec)
        results = {}
 
        # We could do this across hosts or across modules. Not sure
        # which is better, this is across hosts (aka, walk across the
        # hosts, then ask all the module.grep methods to it, then on to
        # next host
        
        existent_minions_class = self.overlord_obj.minions_class # keep a copy
        
        for host in host_modules.keys():
            host_only_mc = self.overlord_obj._mc(host, noglobs=True)
            host_only_mc.get_all_hosts()
            self.overlord_obj.minions_class = host_only_mc
            for module in host_modules[host]:
                if self.options.modules and module in self.options.modules:
                    if self.options.verbose:
                        print "Scanning module: %s on host: %s" %(module, host)
                    
                    tmp_res = self.overlord_obj.run(module,"grep",[self.word])
                
                    if self.options.async:
                        tmp_res = self.overlord_obj.local.utils.async_poll(tmp_res,None)
                    #FIXME: I'm not sure what the best format for this is...
                    if tmp_res[host]:
                        print "%s: %s" % (host, pprint.pformat(tmp_res[host]))
        
        self.overlord_obj.minions_class = existent_minions_class # put it back
        
    def _get_host_grep_modules(self, server_spec):
        """
        In cases when user doesnt supply the module list
        we have to consider that all of the modules are
        chosen so that method will return a list of them
        """
         
        #insetad of getting all of the modules we consider
        #that all of machines has the same modules ...


        host_modules = {}
        #FIXME: we need to change this to create a dict of hostname->modules
        # so we only call module.grep on systems that report it. things like
        # virt/hardware aren't available on all guests
        
        if not hasattr(self, 'overlord_obj'):
            self.getOverlord()
        
        hosts = self.overlord_obj.minions_class.get_all_hosts()
        existent_minions_class = self.overlord_obj.minions_class # keep a copy        
        if not hosts:
            raise Exception("No minions on system!")

        
        for host in hosts:
            host_only_mc = self.overlord_obj._mc(host, noglobs=True)
            self.overlord_obj.minions_class = host_only_mc
            module_methods = self.overlord_obj.system.inventory()

            for hn in module_methods:
                if type(module_methods[hn]) != types.DictType:
                    sys.stderr.write("Error on host %s: %s" % (hn, ' '.join(module_methods[hn])))
                    continue

                for module in module_methods[hn]:
                    # searching for "grep"? meta
                    if "grep" in module_methods[hn][module]:
                        if not host_modules.has_key(host):
                            host_modules[host] = []
                        host_modules[host].append(module)
        
        self.overlord_obj.minions_class = existent_minions_class # put it back
        return host_modules
