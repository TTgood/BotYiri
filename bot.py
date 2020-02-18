from aiocqhttp import CQHttp
from bot_status import Status


class BotYiri(CQHttp):
    NOTHING = 0
    SEND_MESSAGE = 0b000001
    BREAK_OUT = 0b000010
    KICK_OUT = 0b001000
    NOT_AT_SENDER = 0b010000

    def __init__(self, access_token='', console_output=True):
        # pylint: disable=unused-variable
        super(BotYiri, self).__init__(access_token=access_token, enable_http_post=False)
        self._chatters = {}
        self._msg_preprocessors = []
        self._msg_handlers = []
        self._statuses = {}
        

        self.QQID = 0
        
        def get_message_type(context):
            if 'message_type' not in context:
                if 'group_id' in context:
                    return 'group'
                elif 'discuss_id' in context:
                    return 'discuss'
                elif 'user_id' in context:
                    return 'private'
            else:
                return context['message_type']

        # @self.on_meta_event('lifecycle')
        # async def init(context):
        #     rep = await self.get_login_info()
        #     self.QQID = rep['user_id']

        @self.on_message()
        async def handle_message(context):
            message = context.message
            if console_output:
                print('>>> ' + message)
            flags = set([get_message_type(context)])
            for preprocessor, uflags in self._msg_preprocessors:
                dotflags = {flag for flag in flags if flag[0] == '.'}
                if (not uflags and flags - dotflags) or flags & uflags or ('.' in uflags and dotflags):
                    message, flags = preprocessor(message, flags, context)
            report_args = {}
            for handler, uflags in self._msg_handlers:
                dotflags = {flag for flag in flags if flag[0] == '.'}
                if (not uflags and flags - dotflags) or flags & uflags or ('.' in uflags and dotflags):
                    reply, action = handler(message, flags, context)
                    at_sender = (action & self.NOT_AT_SENDER) == 0
                    if action & self.SEND_MESSAGE:
                        await self.send(context, reply, at_sender=at_sender)            
                    if action & self.KICK_OUT:
                        report_args['kick'] = True
                    if action & self.BREAK_OUT:
                        return report_args
            return report_args

        @self.on_meta_event('heartbeat')
        async def check_statuses(context):
            out_of_time = [name for name, st in self._statuses.items() if st.check_timeout()]
            for name in out_of_time:
                del self._statuses[name]
                    

    def msg_preprocessor(self, *args):
        '''
        用于注册消息预处理器的装饰器。
        装饰器接受一个参数，表示响应的处理标志，留空响应所有不以.开头的处理标志，设置为.响应所有以.开有的处理标志。
        消息预处理器接受三个参数：消息（字符串），之前的处理标志（字符串set），消息上下文（dict）
        返回两个参数：修改后的消息（字符串），修改后的处理标志（字符串set）
        '''
        def decorator(func):
            def decorated(message, flags, context):
                result = func(message, flags, context)
                return result if result is not None else (message, flags)
            self._msg_preprocessors.append((decorated, set(args)))
            return decorated
        return decorator

    def msg_handler(self, *args):
        '''
        用于注册消息处理器的装饰器。
        装饰器接受一个参数，表示响应的处理标志，留空响应所有不以.开头的处理标志，设置为.响应所有以.开有的处理标志。
        消息处理器接受三个参数：消息（字符串），处理标志（字符串set），消息上下文（dict）
        返回两个参数：回复信息（字符串），动作信息（整数）
        '''
        def decorator(func):
            def decorated(message, flags, context):
                result = func(message, flags, context)
                return result if result is not None else ('', self.NOTHING)
            self._msg_handlers.append((decorated, set(args)))
            return decorated
        return decorator

    def add_status(self, name, timeout=15, **kwargs):
        st = Status(timeout=timeout, **kwargs)
        self._statuses[name] = st

    def get_status(self, name):
        return self._statuses.get(name, None)
