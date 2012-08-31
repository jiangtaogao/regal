#!/usr/bin/python -B

from string import Template, upper, replace

from ApiUtil import outputCode
from ApiUtil import typeIsVoid

from ApiCodeGen import *

from RegalDispatchLog import apiDispatchFuncInitCode
from RegalDispatchEmu import dispatchSourceTemplate
from RegalContextInfo import cond

##############################################################################################

# CodeGen for API error checking function definition.

def apiErrorFuncDefineCode(apis, args):
  categoryPrev = None
  code = ''

  for api in apis:

    code += '\n'
    if api.name in cond:
      code += '#if %s\n' % cond[api.name]

    for function in api.functions:
      if not function.needsContext:
        continue

      name   = function.name
      params = paramsDefaultCode(function.parameters, True)
      callParams = paramsNameCode(function.parameters)
      rType  = typeCode(function.ret.type)
      category  = getattr(function, 'category', None)
      version   = getattr(function, 'version', None)

      if category:
        category = category.replace('_DEPRECATED', '')
      elif version:
        category = version.replace('.', '_')
        category = 'GL_VERSION_' + category

      # Close prev category block.
      if categoryPrev and not (category == categoryPrev):
        code += '\n'

      # Begin new category block.
      if category and not (category == categoryPrev):
        code += '// %s\n\n' % category

      categoryPrev = category

      code += 'static %sREGAL_CALL %s%s(%s) \n{\n' % (rType, 'error_', name, params)
      code += '  ITrace("error_%s");\n' % name
      code += '  RegalContext *_context = GET_REGAL_CONTEXT();\n'
      code += '  RegalAssert(_context);\n'
      if name != 'glGetError':
        code += '  GLenum _error = GL_NO_ERROR;\n'
        code += '  Dispatcher::ScopedStep stepDown(_context->dispatcher);\n'
        code += '  if (!_context->depthBeginEnd)\n'
        code += '    _error = _context->dispatcher.call(&_context->dispatcher.table().glGetError)();\n'
        code += '  RegalAssert(_error==GL_NO_ERROR);\n'
        code += '  '
        if not typeIsVoid(rType):
          code += '%s ret = ' % rType
        code += '_context->dispatcher.call(&_context->dispatcher.table().%s)(%s);\n' % ( name, callParams )
        code += '  if (!_context->depthBeginEnd) {\n'
        code += '    _error = _context->dispatcher.call(&_context->dispatcher.table().glGetError)();\n'
        code += '    if (_error!=GL_NO_ERROR) {\n'
        code += '      Error("%s : ",Token::GLerrorToString(_error));\n'%(name)
        code += '      if (_context->err.callback)\n'
        code += '        _context->err.callback( _error );\n'
        code += '    }\n'
        code += '  }\n'
        if not typeIsVoid(rType):
          code += 'return ret;\n'
      else:
        code += '  Dispatcher::ScopedStep stepDown(_context->dispatcher);\n'
        code += '  GLenum error = _context->dispatcher.call(&_context->dispatcher.table().glGetError)();\n'
        code += '  return error;\n'
      code += '}\n\n'

    if api.name in cond:
      code += '#endif // %s\n' % cond[api.name]
    code += '\n'

  # Close pending if block.
  if categoryPrev:
    code += '\n'

  return code

def generateErrorSource(apis, args):

  funcDefine = apiErrorFuncDefineCode( apis, args )
  funcInit   = apiDispatchFuncInitCode( apis, args, 'error' )

  substitute = {}
  substitute['LICENSE']         = args.license
  substitute['AUTOGENERATED']   = args.generated
  substitute['COPYRIGHT']       = args.copyright
  substitute['DISPATCH_NAME'] = 'Error'
  substitute['LOCAL_INCLUDE'] = ''
  substitute['LOCAL_CODE']    = ''
  substitute['API_DISPATCH_FUNC_DEFINE'] = funcDefine
  substitute['API_DISPATCH_FUNC_INIT'] = funcInit
  substitute['IFDEF'] = '#if REGAL_ERROR\n\n'
  substitute['ENDIF'] = '#endif\n'
  outputCode( '%s/RegalDispatchError.cpp' % args.outdir, dispatchSourceTemplate.substitute(substitute))