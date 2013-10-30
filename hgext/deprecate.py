#
# Copyright 2013 Brian Mearns ("Maytag Metalark")
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Provides some utility function decorators for marking them deprecated and
replacing them with other names (while preserving the old names).

Copyright 2013 Brian Mearns. You can do whatever you want with it except
hold me responsible.

"""

import functools
import warnings
import sys

class deprecated(object):
    """
    A decorator which marks functions as deprecated. It doesn't actually
    do anything, because we don't want to bug users about something a
    developer did, especially if it was valid when they did it.
    """

    def __init__(self, why=None, file=None, linenum=None):
        if why is None:
            self.__why = ""
        else:
            self.__why = ". " + why

        self.file = file
        self.linenum = linenum

    def __call__(self, func):

        #Wrap the function in one that issues a deprecation warning
        @functools.wraps(func)
        def dfunc(*args, **kwargs):
            warning = "Warning: this function is being deprecated: '%s'%s" % (
                func.__name__, self.__why
            ),

            if self.file is not None and self.linenum is not None:
                warnings.warn_explicit(
                    warning,
                    category=DeprecationWarning,
                    filename=self.file,
                    lineno=self.linenum
                )
            else:
                warnings.warn(
                    warning,
                    category=DeprecationWarning,
                )

            #Now delegate to the original (deprecated) function.
            return func(*args, **kwargs)

        return dfunc

class replace_deprecated(object):
    def __init__(self, old_name, why=None):
        self.old_name = old_name
        self.why = why

    def __call__(self, func):

        #Create a function that will use the old name
        @functools.wraps(func)
        def deprecated_func(*args, **kwargs):
            return func(*args, **kwargs)
        deprecated_func.__name__ = self.old_name

        #Now wrap it up in deprecated.
        if self.why is None:
            self.why = "Use '%s' instead." % func.__name__
        dep = deprecated(
            self.why, func.func_code.co_filename,
            func.func_code.co_firstlineno + 1
        )
        df = dep(deprecated_func)

        #And add that to the global scope.
        mod = (sys.modules[func.__module__])
        setattr(mod, self.old_name, df)

        #Return the original function, we didn't actually want to modify that.
        return func


if __name__ == "__main__":

    @replace_deprecated("my_old_func")
    def myoldfunc(x, y, *args, **opts):
        """This is my docstring."""
        print "Hello, friend!", x, y, args, opts

    #To see the deprecation warning:
    #warnings.simplefilter("always")

    print "Invoking preferred funcname..."
    myoldfunc(10, 15, "artichoke", "bedbug", foo="bar", lamb=20)
    print "Name: " + myoldfunc.__name__
    print "Doc: " + myoldfunc.__doc__

    print ""
    print ""
    print ""
    print "Invoking deprecated funcname..."
    my_old_func(54, 20, "Bananana", trot="burger", fud=None)
    print "Name: " + my_old_func.__name__
    print "Doc: " + my_old_func.__doc__

