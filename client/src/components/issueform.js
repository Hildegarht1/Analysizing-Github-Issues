import React, { useState } from 'react';

const IssueForm = () => {
 const [title, setTitle] = useState('');
 const [body, setBody] = useState('');
 const [prediction, setPrediction] = useState(null);
 const [confidence, setConfidence] = useState(null);
 const [isLoading, setIsLoading] = useState(false);
 const [error, setError] = useState(null);

 const detectLanguage = (text) => {
   const nonEnglishPattern = /[^\x00-\x7F]/;
   if (nonEnglishPattern.test(text)) {
     return 'non-en';
   }

   const words = text.toLowerCase().split(/\s+/);
   const commonEnglishWords = new Set([
     'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 'it',
     'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at', 'this',
     'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she', 'or',
     'will', 'my', 'all', 'would', 'there', 'their', 'is', 'bug', 'issue',
     'error', 'problem', 'feature', 'request', 'can', 'please', 'when', 'what',
     'why', 'how', 'does', 'work', 'need', 'want', 'should', 'could', 'would'
   ]);

   const englishWordCount = words.filter(word => commonEnglishWords.has(word)).length;
   const ratio = englishWordCount / words.length;

   return ratio >= 0.3 ? 'en' : 'non-en';
 };

 const getConfidenceColor = (score) => {
   if (score >= 0.8) return 'text-green-600';
   if (score >= 0.5) return 'text-yellow-600';
   return 'text-red-600';
 };

 const handleInput = (setter) => (e) => {
   setter(e.target.value);
   setPrediction(null);
   setConfidence(null);
 };

 const handlePredict = async () => {
   setIsLoading(true);
   setError(null);

   const combinedText = `${title}\n${body}`;
   const language = detectLanguage(combinedText);

   if (language !== 'en') {
     setError('Kindly stick to English texts only!');
     setIsLoading(false);
     return;
   }

   try {
     const response = await fetch('http://localhost:5000/api/predict', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
       },
       body: JSON.stringify({
         issue_body: combinedText,
       }),
     });

     if (!response.ok) {
       throw new Error('Failed to get prediction');
     }

     const data = await response.json();
     setPrediction(data.predicted_label);
     setConfidence(data.confidence_score);
   } catch (err) {
     setError(err.message);
   } finally {
     setIsLoading(false);
   }
 };

 return (
   <div className="max-w-4xl mx-auto p-6">
     <div className="grid grid-cols-2 gap-6">
       <div className="space-y-4">
         <div>
           <label className="block text-sm font-medium text-gray-700">Title:</label>
           <input
             type="text"
             value={title}
             onChange={handleInput(setTitle)}
             className="w-full p-2 border border-gray-300 rounded"
           />
         </div>

         <div>
           <label className="block text-sm font-medium text-gray-700">Body:</label>
           <textarea
             value={body}
             onChange={handleInput(setBody)}
             className="w-full p-2 border border-gray-300 rounded h-64"
           />
         </div>

         <button
           onClick={handlePredict}
           disabled={isLoading || !title || !body}
           className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-300"
         >
           {isLoading ? 'Predicting...' : 'Predict'}
         </button>
       </div>

       <div className="border-l pl-6">
         <h3 className="text-lg font-medium mb-4">Predicted label:</h3>
         <div className="space-y-2">
           {['Enhancement', 'Bug', 'Question'].map((label) => (
             <label key={label} className="flex items-center space-x-2">
               <input
                 type="radio"
                 checked={prediction === label.toLowerCase()}
                 readOnly
                 className="h-4 w-4"
               />
               <span>{label}</span>
             </label>
           ))}
         </div>

         {confidence && (
           <div className="mt-4">
             <p className="text-sm font-medium text-gray-700">
               Model Confidence:
               <span className={`ml-2 ${getConfidenceColor(confidence)}`}>
                 {(confidence * 100).toFixed(1)}%
               </span>
             </p>
           </div>
         )}
       </div>
     </div>

     {error && (
       <div className="mt-4 p-3 bg-red-100 text-red-700 rounded">
         {error}
       </div>
     )}
   </div>
 );
};

export default IssueForm;