const express = require('express');
const app = express();
app.use(express.json());

const port = process.env.PORT || 3001;
const processorName = process.env.PROCESSOR_NAME || 'Processor';
const failureRate = parseFloat(process.env.FAILURE_RATE) || 0.1; // 10% failure rate

app.post('/process', (req, res) => {
  if (Math.random() < failureRate) {
    return res.status(500).send({ message: `${processorName} failed to process payment.` });
  }
  
  console.log(`[${processorName}] Processing payment for:`, req.body);
  res.status(200).send({ 
    message: `${processorName} processed payment successfully.`,
    transactionId: `txn_${processorName.toLowerCase()}_${Date.now()}` 
  });
});

app.listen(port, () => {
  console.log(`${processorName} listening on port ${port}`);
});
