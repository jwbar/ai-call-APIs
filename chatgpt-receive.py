const express = require('express');
const twilio = require('twilio');
const axios = require('axios');
const app = express();
const VoiceResponse = twilio.twiml.VoiceResponse;

app.post('/voice', async (req, res) => {
  const gather = new VoiceResponse().gather({ input: 'speech', action: '/process' });
  gather.say('Hello, how can I assist you today?');
  res.type('text/xml');
  res.send(gather.toString());
});

app.post('/process', async (req, res) => {
  const userInput = req.body.SpeechResult;
  const response = await axios.post('https://api.openai.com/v1/engines/gpt-4/completions', {
    prompt: `You are an automated assistant. Respond to: ${userInput}`,
    max_tokens: 50
  }, {
    headers: { 'Authorization': `Bearer YOUR_API_KEY` }
  });

  const twiml = new VoiceResponse();
  twiml.say(response.data.choices[0].text.trim());
  res.type('text/xml');
  res.send(twiml.toString());
});

app.listen(3000, () => console.log('Server running on port 3000'));
