# 接收消息格式：
```
{
    "self_id": 3766543953,
    "user_id": 1121053165,
    "time": 1776396413,
    "message_id": 2016829551,
    "message_seq": 2016829551,
    "real_id": 2016829551,
    "real_seq": "142333",
    "message_type": "group",
    "sender": {
        "user_id": 1121053165,
        "nickname": "Hello World",
        "card": "",
        "role": "owner"
    },
    "raw_message": "[CQ:at,qq=3766543953] 你好呀！",
    "font": 14,
    "sub_type": "normal",
    "message": [
        {
            "type": "at",
            "data": {
                "qq": "3766543953"
            }
        },
        {
            "type": "text",
            "data": {
                "text": " 你好呀！"
            }
        }
    ],
    "message_format": "array",
    "post_type": "message",
    "group_id": 1026345080,
    "group_name": "测试"
}
```

# 发送消息格式
```
{
  "action": "send_group_msg",
  "params": {
    "group_id": 123456,
    "message": "大家好！"
  }
}
```