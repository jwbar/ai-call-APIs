require('dotenv').config();
const express = require('express');
const twilio = require('twilio');
const axios = require('axios');

const app = express();
app.use(express.urlencoded({ extended: true }));

const client = new twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);

// Endpoint to initiate an outbound call
app.post('/make-call', async (req, res) => {
    const { to, message } = req.body;  // Caller number and prompt message

    client.calls
        .create({
            url: 'https://your-server.com/handle-call',  // Webhook for handling conversation
            to: to,
            from: process.env.TWILIO_PHONE_NUMBER
        })
        .then(call => res.json({ success: true, callSid: call.sid }))
        .catch(err => res.status(500).json({ success: false, error: err.message }));
});

// Webhook to handle call interaction
app.post('/handle-call', (req, res) => {
    const response = new twilio.twiml.VoiceResponse();
    response.say('Hello! This is an automated assistant. Please say something and I will respond.');
    response.gather({
        input: 'speech',
        action: '/process-speech'
    });

    res.type('text/xml').send(response.toString());
});

// Process speech and respond using GPT-4
app.post('/process-speech', async (req, res) => {
    const userInput = req.body.SpeechResult;

    try {
        const aiResponse = await axios.post(
            'https://api.openai.com/v1/chat/completions',
            {
                model: 'gpt-4',
                messages: [{ role: 'system', content: 'You are an AI secretary handling a phone call.' },
                           { role: 'user', content: userInput }],
                max_tokens: 100
            },
            { headers: { 'Authorization': `Bearer ${process.env.OPENAI_API_KEY}` } }
        );

        const responseText = aiResponse.data.choices[0].message.content.trim();
        const twiml = new twilio.twiml.VoiceResponse();
        twiml.say(responseText);
        twiml.redirect('/handle-call');  // Keep the conversation going

        res.type('text/xml').send(twiml.toString());
    } catch (error) {
        console.error(error);
        const errorResponse = new twilio.twiml.VoiceResponse();
        errorResponse.say("I'm sorry, but I couldn't process that. Let's try again.");
        errorResponse.redirect('/handle-call');
        res.type('text/xml').send(errorResponse.toString());
    }
});

app.listen(3000, () => console.log('Server running on port 3000'));
