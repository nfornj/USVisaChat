import { Sparkles, FileQuestion, Clock, MapPin } from "lucide-react";

interface WelcomeProps {
  onSendMessage: (content: string) => void;
}

export default function Welcome({ onSendMessage }: WelcomeProps) {
  const examples = [
    {
      icon: FileQuestion,
      text: "What documents do I need for H1B visa stamping?",
      color: "text-blue-600 dark:text-blue-400",
    },
    {
      icon: Clock,
      text: "How long does F1 visa processing usually take?",
      color: "text-green-600 dark:text-green-400",
    },
    {
      icon: MapPin,
      text: "What is the interview experience at Mumbai consulate?",
      color: "text-purple-600 dark:text-purple-400",
    },
    {
      icon: Sparkles,
      text: "Tell me about dropbox eligibility requirements",
      color: "text-orange-600 dark:text-orange-400",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="mb-8">
        <div className="w-20 h-20 bg-gradient-to-br from-primary-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Sparkles className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
          Visa Assistant
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-lg max-w-2xl">
          Search through 1.5M+ visa conversations to get answers about visa
          processes, requirements, and experiences
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl w-full">
        {examples.map((example, idx) => (
          <button
            key={idx}
            onClick={() => onSendMessage(example.text)}
            className="group text-left p-4 rounded-xl border-2 border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-500 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
          >
            <div className="flex items-start gap-3">
              <example.icon
                className={`w-6 h-6 flex-shrink-0 ${example.color}`}
              />
              <div>
                <p className="text-gray-900 dark:text-white font-medium group-hover:text-primary-600 dark:group-hover:text-primary-400">
                  {example.text}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-8 text-sm text-gray-500 dark:text-gray-400">
        <p>Try asking me anything about:</p>
        <p className="mt-1">
          • Visa requirements • Processing times • Interview experiences •
          Document lists • Appointment scheduling
        </p>
      </div>
    </div>
  );
}





