import type { MessageInstance } from 'antd/es/message/interface';

let _message: MessageInstance | null = null;

export function setMessageInstance(instance: MessageInstance) {
  _message = instance;
}

export function getMessageInstance(): MessageInstance {
  if (!_message) {
    throw new Error('Message instance not initialized. Call setMessageInstance first.');
  }
  return _message;
}
