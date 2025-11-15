// 前端发送验证码请求（src/services/agcService.js）
export const sendVerificationCode = async (phone) => {
  const url = '/api/send-code'; // 对应 AGC 云函数路径
  const headers = {
    'x-agc-api-key': process.env.REACT_APP_AGC_API_KEY,
  };
  return fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({ phone }),
  });
};

// 登录页组件（src/pages/Login/index.jsx）
const Login = () => {
  const handleGetCode = async () => {
    try {
      await sendVerificationCode('13508234986');
      message.success('验证码已发送');
    } catch (error) {
      console.error(error);
      message.error('获取验证码失败');
    }
  };

  return (
    <Button onClick={handleGetCode}>获取验证码</Button>
  );
};