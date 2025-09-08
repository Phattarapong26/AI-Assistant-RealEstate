import { useState, useRef, useEffect, useContext } from "react";
import { Send, Loader, ImageOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { sendChatMessage, getChatRoomHistory, saveChatHistory } from "../frontend/api";
import { createContext } from "react";
import { useChats } from "@/hooks/useChats";
import { useParams } from "react-router-dom";

interface Message {
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  properties?: Array<Record<string, string>>;
}

interface ConsultationStyle {
  id: string;
  name: string;
  description: string;
  emojis: string[];
  phrases: {
    greeting: string[];
    positive: string[];
    neutral: string[];
    negative: string[];
    closing: string[];
  };
}

const consultationStyles: Record<string, ConsultationStyle> = {
  formal: {
    id: "formal",
    name: "ทางการ",
    description: "สไตล์การสนทนาแบบทางการ เหมาะสำหรับลูกค้าที่ต้องการความเป็นมืออาชีพ",
    emojis: ["🏢", "📊", "✓"],
    phrases: {
      greeting: [
        "ยินดีให้บริการค่ะ",
        "สวัสดีครับ ยินดีให้คำปรึกษาด้านอสังหาริมทรัพย์",
        "ขอขอบคุณที่ใช้บริการของเรา"
      ],
      positive: [
        "ขอนำเสนอข้อมูลที่ตรงตามความต้องการของท่าน",
        "ทางเรามีข้อมูลอสังหาริมทรัพย์ที่น่าสนใจสำหรับท่าน",
        "จากการวิเคราะห์ความต้องการของท่าน"
      ],
      neutral: [
        "ขออนุญาตนำเสนอข้อมูลเพิ่มเติม",
        "ท่านสามารถพิจารณาตัวเลือกต่อไปนี้",
        "ขอเสนอทางเลือกที่เหมาะสม"
      ],
      negative: [
        "ขออภัยครับ ทางเราไม่พบข้อมูลที่ตรงตามความต้องการ",
        "ขอแจ้งให้ทราบว่าขณะนี้ไม่มีข้อมูลในระบบ",
        "ต้องขออภัยในความไม่สะดวก"
      ],
      closing: [
        "หากมีข้อสงสัยประการใด ท่านสามารถสอบถามเพิ่มเติมได้ตลอดเวลา",
        "ทางเรายินดีให้บริการท่านเสมอ",
        "ขอบคุณที่ใช้บริการของเรา"
      ]
    }
  },
  casual: {
    id: "casual",
    name: "ทั่วไป",
    description: "สไตล์การสนทนาแบบทั่วไป เป็นกันเองแต่ยังคงความเป็นมืออาชีพ",
    emojis: ["🏠", "👍", "💬"],
    phrases: {
      greeting: [
        "สวัสดีครับ มีอะไรให้ช่วยไหม",
        "เฮ้ มีอะไรให้ช่วยด้านอสังหาฯ บ้าง",
        "ว่าไงครับ สนใจอสังหาฯ แบบไหนอยู่"
      ],
      positive: [
        "เรามีตัวเลือกดีๆ มาแนะนำ",
        "นี่เลย ลองดูตัวนี้สิ น่าจะถูกใจ",
        "มีอสังหาฯ ที่น่าสนใจตามนี้เลย"
      ],
      neutral: [
        "ลองดูข้อมูลพวกนี้ก่อนไหม",
        "เรามีตัวเลือกให้ดูหลายแบบ",
        "ลองพิจารณาดูทางเลือกพวกนี้"
      ],
      negative: [
        "โอ้ ดูเหมือนเราไม่มีข้อมูลที่คุณต้องการพอดี",
        "ขอโทษนะ ตอนนี้ยังไม่มีข้อมูลแบบที่คุณต้องการ",
        "ยังไม่เจอข้อมูลที่ตรงเป๊ะ ลองถามใหม่ได้ไหม"
      ],
      closing: [
        "มีอะไรสงสัยก็ถามมาได้เลยนะ",
        "ต้องการอะไรเพิ่มก็บอกได้",
        "ยังไงก็ติดต่อกลับมาได้ตลอด"
      ]
    }
  },
  friendly: {
    id: "friendly",
    name: "เป็นกันเอง",
    description: "สไตล์การสนทนาแบบเป็นกันเอง เหมือนคุยกับเพื่อน",
    emojis: ["😊", "🏡", "💕", "✨"],
    phrases: {
      greeting: [
        "สวัสดีค่าา~ มีอะไรให้ช่วยบ้างคะ",
        "ว่าไงคะ วันนี้อยากได้บ้านแบบไหนเอ่ย",
        "สวัสดีจ้า~ อยากรู้อะไรเกี่ยวกับอสังหาฯ บ้างคะ"
      ],
      positive: [
        "เจอแล้วล่ะ! มีตัวที่น่าสนใจมากๆ เลยนะคะ",
        "โอ้โห! ดูนี่สิคะ น่าจะถูกใจแน่นอน",
        "ยินดีด้วยค่ะ! เรามีตัวเลือกดีๆ มาแนะนำเลย"
      ],
      neutral: [
        "เรามีตัวเลือกหลากหลายเลยนะคะ ลองดูกันไหม",
        "เดี๋ยวหาให้ดูนะคะ มีหลายแบบเลย",
        "นี่ค่ะ ลองดูตัวเลือกพวกนี้ก่อนนะ"
      ],
      negative: [
        "อุ๊ย! ขอโทษนะคะ ตอนนี้ยังไม่มีข้อมูลที่ตรงกับที่ต้องการพอดีเลย",
        "แย่จัง~ ยังไม่มีข้อมูลในระบบเลยค่ะ",
        "โอ๊ะ! ยังไม่เจอสิ่งที่กำลังตามหาเลย ลองเปลี่ยนคำค้นหาดูไหมคะ"
      ],
      closing: [
        "มีอะไรอยากรู้เพิ่มเติมก็ถามมาได้เลยนะคะ ยินดีช่วยเหลือเสมอค่ะ",
        "ถ้ายังมีข้อสงสัยอะไร ทักมาได้ตลอดเลยนะคะ",
        "แวะมาคุยใหม่ได้ตลอดเลยนะคะ ยินดีให้คำปรึกษาจ้า~"
      ]
    }
  },
  professional: {
    id: "professional",
    name: "มืออาชีพ",
    description: "สไตล์การสนทนาแบบมืออาชีพ เหมาะสำหรับลูกค้าที่ต้องการข้อมูลเชิงลึก",
    emojis: ["📈", "🔍", "📑", "💼"],
    phrases: {
      greeting: [
        "สวัสดีครับ ผมยินดีให้คำปรึกษาด้านอสังหาริมทรัพย์แบบมืออาชีพ",
        "ขอบคุณที่ให้ความไว้วางใจในบริการของเรา",
        "สวัสดีครับ ผมพร้อมให้คำแนะนำและวิเคราะห์อสังหาริมทรัพย์ที่เหมาะสมกับความต้องการของคุณ"
      ],
      positive: [
        "จากการวิเคราะห์ข้อมูลตลาดอสังหาริมทรัพย์ล่าสุด ผมขอนำเสนอทางเลือกที่ผ่านการคัดสรรแล้วดังนี้",
        "หลังจากวิเคราะห์ความต้องการของคุณอย่างละเอียด ผมได้คัดสรรรายการอสังหาริมทรัพย์ที่ตรงตามเกณฑ์ดังนี้",
        "ด้วยประสบการณ์กว่า 10 ปีในวงการอสังหาริมทรัพย์ ผมขอเสนอตัวเลือกที่คุ้มค่าต่อการลงทุนดังนี้"
      ],
      neutral: [
        "ผมขอนำเสนอข้อมูลเชิงลึกเพื่อประกอบการตัดสินใจของคุณ",
        "โปรดพิจารณาทางเลือกเหล่านี้ซึ่งผ่านการประเมินคุณภาพและมูลค่าในระยะยาวแล้ว",
        "จากการศึกษาข้อมูลตลาดและทำเลที่ตั้ง ผมขอเสนอตัวเลือกที่มีศักยภาพดังนี้"
      ],
      negative: [
        "ผมต้องแจ้งให้ทราบว่า ขณะนี้ยังไม่มีอสังหาริมทรัพย์ที่ตรงตามเกณฑ์คุณภาพและความต้องการของคุณในระบบ",
        "จากการตรวจสอบฐานข้อมูลล่าสุด ผมพบว่ายังไม่มีอสังหาริมทรัพย์ที่ตรงตามความต้องการเฉพาะของคุณ",
        "ผมขอเรียนให้ทราบว่า ตามเงื่อนไขที่ระบุ ยังไม่มีอสังหาริมทรัพย์ที่ผ่านเกณฑ์มาตรฐานของเรา"
      ],
      closing: [
        "หากคุณสนใจข้อมูลเชิงลึกเพิ่มเติม ผมพร้อมให้คำปรึกษาและจัดเตรียมรายละเอียดเพิ่มเติมสำหรับคุณ",
        "ผมพร้อมที่จะให้คำแนะนำเพิ่มเติมเกี่ยวกับการลงทุน การจัดการสินทรัพย์ หรือข้อมูลตลาดล่าสุด",
        "ด้วยความเชี่ยวชาญของทีมงานเรา ผมมั่นใจว่าเราสามารถช่วยคุณหาอสังหาริมทรัพย์ที่ตรงกับความต้องการได้"
      ]
    }
  }
};

const consultationStylesEnglish = {
  formal: {
    greeting: [
      "Welcome to our service.",
      "Hello, I'm pleased to provide real estate consulting services.",
      "Thank you for using our service."
    ],
    positive: [
      "I would like to present information that matches your requirements.",
      "We have interesting real estate information for you.",
      "Based on an analysis of your needs."
    ],
    neutral: [
      "I would like to present additional information.",
      "You may consider the following options.",
      "I would like to suggest suitable alternatives."
    ],
    negative: [
      "I apologize, we could not find information that matches your requirements.",
      "I would like to inform you that there is currently no information in the system.",
      "I apologize for the inconvenience."
    ],
    closing: [
      "If you have any questions, you can ask for more information at any time.",
      "We are always pleased to be of service.",
      "Thank you for using our service."
    ]
  },
  casual: {
    greeting: [
      "Hi there, how can I help?",
      "Hey, what can I help you with in real estate?",
      "What's up? What kind of property are you interested in?"
    ],
    positive: [
      "We have some great options to recommend.",
      "Here you go, take a look at this one, you might like it.",
      "Here are some interesting properties."
    ],
    neutral: [
      "Want to check out this information first?",
      "We have several options for you to look at.",
      "Take a look at these alternatives."
    ],
    negative: [
      "Oh, it looks like we don't have the information you need.",
      "Sorry, we don't have the information you're looking for right now.",
      "Haven't found an exact match yet. Could you try asking again?"
    ],
    closing: [
      "If you have any questions, just ask.",
      "Let me know if you need anything else.",
      "Feel free to contact me anytime."
    ]
  },
  friendly: {
    greeting: [
      "Hello there~! How can I help you today?",
      "Hey! What kind of home are you looking for today?",
      "Hi there~! What would you like to know about real estate?"
    ],
    positive: [
      "Found it! I have something really interesting for you!",
      "Wow! Look at this one, you're going to love it!",
      "Congratulations! I have some great options to recommend!"
    ],
    neutral: [
      "We have lots of options for you! Want to take a look?",
      "Let me find some for you! There are so many styles!",
      "Here you go! Check out these options first!"
    ],
    negative: [
      "Oops! Sorry, I don't have any matches for what you're looking for right now!",
      "Oh no~ There's no information in our system yet!",
      "Oh! I haven't found what you're looking for yet. Maybe try a different search term?"
    ],
    closing: [
      "If you want to know anything else, just ask! Always happy to help!",
      "If you have any other questions, message me anytime!",
      "Feel free to chat again anytime! Happy to give advice~!"
    ]
  },
  professional: {
    greeting: [
      "Hello, I'm pleased to provide professional real estate consultation.",
      "Thank you for trusting our services.",
      "Hello, I'm ready to provide recommendations and analyze real estate that suits your specific needs."
    ],
    positive: [
      "Based on the latest real estate market analysis, I would like to present the following carefully selected options.",
      "After thoroughly analyzing your requirements, I have curated a list of real estate properties that meet your criteria as follows.",
      "With over 10 years of experience in the real estate industry, I would like to recommend the following investment-worthy options."
    ],
    neutral: [
      "I would like to present in-depth information to assist with your decision-making process.",
      "Please consider these options, which have been evaluated for quality and long-term value.",
      "Based on market research and location analysis, I would like to suggest the following high-potential options."
    ],
    negative: [
      "I must inform you that currently there are no properties in our system that meet your quality criteria and requirements.",
      "After checking our latest database, I found that there are no properties that match your specific needs.",
      "I would like to inform you that, based on your specified conditions, there are no properties that meet our standard criteria."
    ],
    closing: [
      "If you are interested in more in-depth information, I am ready to provide consultation and prepare additional details for you.",
      "I am ready to provide further advice on investment, asset management, or the latest market data.",
      "With our team's expertise, I am confident that we can help you find real estate that meets your requirements."
    ]
  }
};

const StyleContext = createContext({
  consultationStyle: "formal",
  setConsultationStyle: (style: string) => {},
  language: "thai",
  setLanguage: (lang: string) => {}
});

// Export the StyleContext so it can be imported in other files
export { StyleContext };

export const StyleProvider = ({ children }) => {
  const [consultationStyle, setConsultationStyle] = useState<string>("formal");
  const [language, setLanguage] = useState<string>("thai");
  
  useEffect(() => {
    // โหลดค่า style และ language จาก localStorage เมื่อคอมโพเนนต์โหลด
    const savedStyle = localStorage.getItem("consultationStyle");
    if (savedStyle) {
      setConsultationStyle(savedStyle);
    }
    
    const savedLanguage = localStorage.getItem("language");
    if (savedLanguage) {
      setLanguage(savedLanguage);
    }
  }, []);
  
  // บันทึกการเปลี่ยนแปลง style
  const handleStyleChange = (style: string) => {
    setConsultationStyle(style);
    localStorage.setItem("consultationStyle", style);
  };
  
  // บันทึกการเปลี่ยนแปลง language
  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    localStorage.setItem("language", lang);
  };
  
  return (
    <StyleContext.Provider value={{ 
      consultationStyle, 
      setConsultationStyle: handleStyleChange,
      language,
      setLanguage: handleLanguageChange
    }}>
      {children}
    </StyleContext.Provider>
  );
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [chatRoomId, setChatRoomId] = useState<string | null>(null);
  const [isNewChat, setIsNewChat] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { consultationStyle, language } = useContext(StyleContext);
  const { currentChatId, getChatSession, addMessageToChat } = useChats();
  const { id: chatIdFromUrl } = useParams();

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // เพิ่ม useEffect เพื่อแสดงผลเมื่อ language เปลี่ยน
  useEffect(() => {
    console.log("ค่าภาษาปัจจุบัน:", language);
    console.log("ค่าภาษาใน localStorage:", localStorage.getItem("language"));
    
    // ไม่ต้อง reload ทั้งหมด เพียงเปลี่ยนข้อความทักทาย
    if (messages.length === 1 && messages[0].type === "assistant") {
      setMessages([{
        type: "assistant",
        content: translate(welcomeMessage.thai, welcomeMessage.english, language),
        timestamp: new Date(),
      }]);
    }
  }, [language]);

  useEffect(() => {
    // กำหนด chatRoomId จาก URL params หรือ currentChatId จาก useChats
    const roomId = chatIdFromUrl || currentChatId || localStorage.getItem("chatRoomId");
    
    if (roomId) {
      setChatRoomId(roomId);
      localStorage.setItem("chatRoomId", roomId);
      
      // ตรวจสอบว่าเป็นห้องใหม่หรือไม่
      const chatSession = getChatSession(roomId);
      if (chatSession) {
        const isNewlyCreated = Date.now() - chatSession.createdAt < 5000; // 5 วินาที
        setIsNewChat(isNewlyCreated && chatSession.messages.length === 0);
      }
      
      // โหลดประวัติการสนทนาจากห้อง
      loadChatRoomHistory(roomId);
      console.log("โหลดห้องสนทนา:", roomId);
    }
  }, [chatIdFromUrl, currentChatId]);

  // เพิ่มฟังก์ชันแปลข้อความตามภาษาที่เลือก
  const translate = (thai: string, english: string, language?: string): string => {
    return language === "thai" ? thai : english;
  };

  // ตัวอย่างข้อความสำหรับภาษาอังกฤษ
  const welcomeMessage = {
    thai: "สวัสดีครับ ยินดีต้อนรับสู่ Property AI Guru! คุณสามารถถามคำถามเกี่ยวกับอสังหาริมทรัพย์ได้เลยครับ",
    english: "Hello! Welcome to Property AI Guru! You can ask any questions about real estate."
  };

  const errorMessages = {
    loadHistoryFailed: {
      thai: "เกิดข้อผิดพลาดในการโหลดประวัติการสนทนา",
      english: "Failed to load chat history"
    },
    serverError: {
      thai: "เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้ง",
      english: "Error connecting to server. Please try again."
    }
  };

  // ฟังก์ชันโหลดประวัติการสนทนาในห้อง
  const loadChatRoomHistory = async (roomId: string) => {
    try {
      console.log("กำลังโหลดประวัติห้องสนทนา:", roomId);
      // ตรวจสอบก่อนว่ามีข้อมูลใน local state (useChats) หรือไม่
      const chatSession = getChatSession(roomId);
      
      if (chatSession && chatSession.messages.length > 0) {
        // ถ้ามีข้อมูลใน local state ให้ใช้ข้อมูลนั้น
        const formattedMessages = chatSession.messages.map(msg => ({
          type: msg.role === "user" ? "user" : "assistant",
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          properties: msg.properties || []
        } as Message));
        
        console.log("พบข้อความในห้องสนทนา:", formattedMessages.length);
        // แก้ไขเป็น set messages โดยตรงแทนที่จะเติมจาก messages[0]
        setMessages(formattedMessages.length > 0 ? formattedMessages : [
          {
            type: "assistant",
            content: translate(welcomeMessage.thai, welcomeMessage.english, language),
            timestamp: new Date(),
          }
        ]);
        
        // แสดงการโหลดข้อมูลสำหรับแชทเก่า
        if (!isNewChat) {
          toast.info(translate(
            `โหลดประวัติสนทนา (${formattedMessages.length} ข้อความ)`, 
            `Loaded chat history (${formattedMessages.length} messages)`,
            language
          ));
        }
      } else {
        // ทดลองโหลดจาก API ก่อน ถ้ามี backend รองรับ
        try {
          const historyFromApi = await getChatRoomHistory(roomId);
          if (historyFromApi && historyFromApi.messages && historyFromApi.messages.length > 0) {
            const formattedMessages = historyFromApi.messages.map(msg => ({
              type: msg.role === "user" ? "user" : "assistant",
              content: msg.content,
              timestamp: new Date(msg.timestamp),
              properties: msg.properties || []
            } as Message));
            
            console.log("โหลดประวัติจาก API สำเร็จ:", formattedMessages.length, "ข้อความ");
            setMessages(formattedMessages);
            toast.info(translate(
              `โหลดประวัติสนทนาจากเซิร์ฟเวอร์ (${formattedMessages.length} ข้อความ)`,
              `Loaded chat history from server (${formattedMessages.length} messages)`,
              language
            ));
            return;
          }
        } catch (apiError) {
          console.warn("ไม่สามารถโหลดประวัติจาก API ได้:", apiError);
          // ไม่ต้อง error หรือ toast เพราะจะใช้ local fallback
        }
        
        // ถ้าเป็นแชทใหม่หรือไม่มีข้อความในแชท ให้รีเซ็ตเป็นข้อความต้อนรับเริ่มต้น
        console.log("ไม่พบข้อความในห้องสนทนา หรือเป็นห้องสนทนาใหม่");
        setMessages([
          {
            type: "assistant",
            content: translate(welcomeMessage.thai, welcomeMessage.english, language),
            timestamp: new Date(),
          }
        ]);
        
        // แสดง toast ตามสถานะ isNewChat
        if (isNewChat) {
          toast.success(translate(
            "สร้างห้องสนทนาใหม่เรียบร้อย",
            "New chat room created successfully",
            language
          ));
        }
      }
    } catch (error) {
      console.error("Error loading chat history:", error);
      // กรณีเกิดข้อผิดพลาด ให้แสดงข้อความต้อนรับเริ่มต้น
      setMessages([
        {
          type: "assistant",
          content: translate(welcomeMessage.thai, welcomeMessage.english, language),
          timestamp: new Date(),
        }
      ]);
      toast.error(translate(
        errorMessages.loadHistoryFailed.thai,
        errorMessages.loadHistoryFailed.english,
        language
      ));
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Function to get a random phrase from the selected style
  const getRandomPhrase = (category: 'greeting' | 'positive' | 'neutral' | 'negative' | 'closing') => {
    const style = consultationStyles[consultationStyle];
    const styleEnglish = consultationStylesEnglish[consultationStyle as keyof typeof consultationStylesEnglish];
    
    const phrases = style.phrases[category];
    const phrasesEnglish = styleEnglish[category];
    
    const randomIndex = Math.floor(Math.random() * phrases.length);
    
    return language === 'thai' ? phrases[randomIndex] : phrasesEnglish[randomIndex];
  };

  // Function to get random emojis for the selected style
  const getRandomEmoji = () => {
    const style = consultationStyles[consultationStyle];
    return style.emojis[Math.floor(Math.random() * style.emojis.length)];
  };

  // Function to enhance property descriptions based on consultation style
  const enhancePropertyDescription = (property: Record<string, string>) => {
    const style = consultationStyles[consultationStyle];
    const emoji = getRandomEmoji();
    
    let enhancedDescription = '';
    
    // Add style-based intro
    const positivePhrase = getRandomPhrase('positive');
    enhancedDescription += `${positivePhrase}\n\n`;
    
    // Format the property information in a more natural way
    if (property["ประเภท"] && property["โครงการ"]) {
      if (consultationStyle === 'formal') {
        enhancedDescription += language === 'thai' 
          ? `${emoji} ทรัพย์สินประเภท${property["ประเภท"]} ภายใต้โครงการ${property["โครงการ"]}`
          : `${emoji} Property type: ${property["ประเภท"]} under the ${property["โครงการ"]} project`;
      } else if (consultationStyle === 'casual') {
        enhancedDescription += language === 'thai'
          ? `${emoji} เป็น${property["ประเภท"]}ในโครงการ${property["โครงการ"]}`
          : `${emoji} This is a ${property["ประเภท"]} in the ${property["โครงการ"]} project`;
      } else if (consultationStyle === 'friendly') {
        enhancedDescription += language === 'thai'
          ? `${emoji} น่าสนใจมากเลยค่ะ! ${property["ประเภท"]}สวยๆ ในโครงการ${property["โครงการ"]}`
          : `${emoji} This is so exciting! A beautiful ${property["ประเภท"]} in the ${property["โครงการ"]} project`;
      } else if (consultationStyle === 'professional') {
        enhancedDescription += language === 'thai'
          ? `${emoji} อสังหาริมทรัพย์ประเภท${property["ประเภท"]} ในโครงการคุณภาพอย่าง${property["โครงการ"]}`
          : `${emoji} A premium ${property["ประเภท"]} real estate in the high-quality ${property["โครงการ"]} development`;
      }
    }
    
    if (property["รูปแบบ"]) {
      if (consultationStyle === 'formal') {
        enhancedDescription += language === 'thai'
          ? ` รูปแบบ${property["รูปแบบ"]}`
          : ` Style: ${property["รูปแบบ"]}`;
      } else if (consultationStyle === 'casual') {
        enhancedDescription += language === 'thai'
          ? ` เป็นแบบ${property["รูปแบบ"]}`
          : ` with a ${property["รูปแบบ"]} style`;
      } else if (consultationStyle === 'friendly') {
        enhancedDescription += language === 'thai'
          ? ` แบบ${property["รูปแบบ"]} สวยมากเลยค่ะ`
          : ` with a gorgeous ${property["รูปแบบ"]} style!`;
      } else if (consultationStyle === 'professional') {
        enhancedDescription += language === 'thai'
          ? ` ออกแบบในรูปแบบ${property["รูปแบบ"]} ที่ได้มาตรฐาน`
          : ` designed in a standard-compliant ${property["รูปแบบ"]} style`;
      }
    }
    
    if (property["ราคา"]) {
      if (consultationStyle === 'formal') {
        enhancedDescription += language === 'thai'
          ? ` ราคา ${property["ราคา"]} บาท`
          : ` Price: ${property["ราคา"]} THB`;
      } else if (consultationStyle === 'casual') {
        enhancedDescription += language === 'thai'
          ? ` ราคา ${property["ราคา"]} บาท ถือว่าคุ้มค่า`
          : ` Price: ${property["ราคา"]} THB, which is good value`;
      } else if (consultationStyle === 'friendly') {
        enhancedDescription += language === 'thai'
          ? ` ราคาเพียง ${property["ราคา"]} บาทเท่านั้นค่ะ คุ้มมาก!`
          : ` Priced at only ${property["ราคา"]} THB! Such great value!`;
      } else if (consultationStyle === 'professional') {
        enhancedDescription += language === 'thai'
          ? ` มูลค่าการลงทุนที่ ${property["ราคา"]} บาท ซึ่งเป็นราคาที่เหมาะสมกับคุณภาพและทำเล`
          : ` Investment value of ${property["ราคา"]} THB, which is appropriate for the quality and location`;
      }
    }
    
    // Add nearby facilities with style-appropriate wording
    const nearbyFacilities = [];
    
    if (property["สถานศึกษา"] && property["สถานศึกษา"] !== "ไม่มี") {
      if (consultationStyle === 'formal') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้สถานศึกษา${property["สถานศึกษา"]}`
          : `near the ${property["สถานศึกษา"]} educational institution`);
      } else if (consultationStyle === 'casual') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้${property["สถานศึกษา"]} สะดวกมาก`
          : `close to ${property["สถานศึกษา"]}, very convenient`);
      } else if (consultationStyle === 'friendly') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้${property["สถานศึกษา"]} เดินทางสะดวกสุดๆ เลยค่ะ`
          : `near ${property["สถานศึกษา"]}, super convenient!`);
      } else if (consultationStyle === 'professional') {
        nearbyFacilities.push(language === 'thai'
          ? `อยู่ในรัศมีการเดินทางที่เหมาะสมจากสถาบันการศึกษาชั้นนำอย่าง${property["สถานศึกษา"]}`
          : `within an appropriate travel radius from leading educational institutions like ${property["สถานศึกษา"]}`);
      }
    }
    
    if (property["สถานีรถไฟฟ้า"] && property["สถานีรถไฟฟ้า"] !== "ไม่มี") {
      if (consultationStyle === 'formal') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้สถานีรถไฟฟ้า${property["สถานีรถไฟฟ้า"]}`
          : `near ${property["สถานีรถไฟฟ้า"]} mass transit station`);
      } else if (consultationStyle === 'casual') {
        nearbyFacilities.push(language === 'thai'
          ? `เดินถึงรถไฟฟ้า${property["สถานีรถไฟฟ้า"]} ง่ายๆ เลย`
          : `easy walking distance to ${property["สถานีรถไฟฟ้า"]} station`);
      } else if (consultationStyle === 'friendly') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้รถไฟฟ้า${property["สถานีรถไฟฟ้า"]} แค่ไม่กี่ก้าวเท่านั้น สะดวกมากๆ ค่ะ`
          : `just steps away from ${property["สถานีรถไฟฟ้า"]} station, so convenient!`);
      } else if (consultationStyle === 'professional') {
        nearbyFacilities.push(language === 'thai'
          ? `มีความได้เปรียบด้านทำเลที่เข้าถึงระบบขนส่งมวลชนได้สะดวกผ่านสถานีรถไฟฟ้า${property["สถานีรถไฟฟ้า"]}`
          : `offers a strategic location advantage with convenient access to public transportation via ${property["สถานีรถไฟฟ้า"]} station`);
      }
    }
    
    if (property["ห้างสรรพสินค้า"] && property["ห้างสรรพสินค้า"] !== "ไม่มี") {
      if (consultationStyle === 'formal') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้ห้างสรรพสินค้า${property["ห้างสรรพสินค้า"]}`
          : `near ${property["ห้างสรรพสินค้า"]} shopping mall`);
      } else if (consultationStyle === 'casual') {
        nearbyFacilities.push(language === 'thai'
          ? `ช้อปปิ้งง่ายที่${property["ห้างสรรพสินค้า"]} ใกล้ๆ เลย`
          : `easy shopping at nearby ${property["ห้างสรรพสินค้า"]}`);
      } else if (consultationStyle === 'friendly') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้ห้าง${property["ห้างสรรพสินค้า"]} ช้อปปิ้งสบายๆ ไม่ต้องเดินทางไกลเลยค่ะ`
          : `near ${property["ห้างสรรพสินค้า"]} mall, shop easily without traveling far!`);
      } else if (consultationStyle === 'professional') {
        nearbyFacilities.push(language === 'thai'
          ? `ตั้งอยู่ใกล้ศูนย์การค้า${property["ห้างสรรพสินค้า"]} ซึ่งมีสิ่งอำนวยความสะดวกครบครัน`
          : `located near ${property["ห้างสรรพสินค้า"]} shopping center with comprehensive amenities`);
      }
    }
    
    if (property["โรงพยาบาล"] && property["โรงพยาบาล"] !== "ไม่มี") {
      if (consultationStyle === 'formal') {
        nearbyFacilities.push(language === 'thai'
          ? `ใกล้โรงพยาบาล${property["โรงพยาบาล"]}`
          : `near ${property["โรงพยาบาล"]} Hospital`);
      } else if (consultationStyle === 'casual') {
        nearbyFacilities.push(language === 'thai'
          ? `มีโรงพยาบาล${property["โรงพยาบาล"]} อยู่ใกล้ๆ ปลอดภัย`
          : `${property["โรงพยาบาล"]} Hospital is nearby, safe and secure`);
      } else if (consultationStyle === 'friendly') {
        nearbyFacilities.push(language === 'thai'
          ? `อุ่นใจได้เลยค่ะ มีโรงพยาบาล${property["โรงพยาบาล"]} อยู่ไม่ไกล`
          : `peace of mind with ${property["โรงพยาบาล"]} Hospital not far away!`);
      } else if (consultationStyle === 'professional') {
        nearbyFacilities.push(language === 'thai'
          ? `ด้านสาธารณสุข อยู่ในรัศมีให้บริการของโรงพยาบาลชั้นนำอย่าง${property["โรงพยาบาล"]}`
          : `for healthcare needs, within the service radius of leading medical facility ${property["โรงพยาบาล"]} Hospital`);
      }
    }
    
    if (nearbyFacilities.length > 0) {
      enhancedDescription += language === 'thai'
        ? `\n\nข้อดีของทำเลนี้คือ ${nearbyFacilities.join(' และ')}`
        : `\n\nThe advantages of this location include ${nearbyFacilities.join(' and ')}`;
    }
    
    return enhancedDescription;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    // Add user message
    const userMessage: Message = {
      type: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      // เพิ่มข้อความผู้ใช้ลงใน local state ก่อนเรียก API
      if (chatRoomId) {
        addMessageToChat(chatRoomId, {
          role: "user",
          content: inputValue,
          timestamp: Date.now()
        });
      }
      
      // Call the backend API
      const response = await sendChatMessage({
        query: inputValue,
        consultation_style: consultationStyle,
        chat_room_id: chatRoomId || undefined,
        language: language
      });
      
      // Save the chat room ID
      if (response.chat_room_id) {
        setChatRoomId(response.chat_room_id);
        localStorage.setItem("chatRoomId", response.chat_room_id);
      } else if (response.session_id) {
        // รองรับกรณีที่ API ยังส่งกลับมาแบบเดิม
        const sessionId = response.session_id;
        setChatRoomId(sessionId);
        localStorage.setItem("chatRoomId", sessionId);
      }
      
      // Create enhanced property descriptions if properties exist
      let enhancedResponse = response.response;
      
      // If there are properties, replace the plain text with enhanced descriptions
      if (response.properties && response.properties.length > 0) {
        // Get the closing phrase based on style
        const closingPhrase = getRandomPhrase('closing');
        
        // Create enhanced descriptions for each property
        const enhancedProperties = response.properties.map((property, index) => {
          const propertyLabel = language === 'thai' ? `Property ${index + 1}` : `Property ${index + 1}`;
          return `${propertyLabel}\n${enhancePropertyDescription(property)}`;
        }).join('\n\n');
        
        // Combine with appropriate introduction and closing
        enhancedResponse = `${getRandomPhrase('positive')}\n\n${enhancedProperties}\n\n${closingPhrase}`;
      } else {
        // ตรวจสอบว่าเป็นการตอบแบบไม่พบข้อมูลหรือไม่
        const thaiNoDataPhrases = ["ไม่พบข้อมูล", "ไม่เจอข้อมูล", "ไม่มีข้อมูล"];
        const englishNoDataPhrases = ["no data found", "no information available", "couldn't find any information", "don't have information", "don't have data", "not found"];
        
        // กรณีตอบแบบไม่พบข้อมูล
        const isThaiNoDataResponse = thaiNoDataPhrases.some(phrase => response.response.includes(phrase));
        const isEnglishNoDataResponse = englishNoDataPhrases.some(phrase => response.response.toLowerCase().includes(phrase));
        
        if (isThaiNoDataResponse || isEnglishNoDataResponse) {
          // สร้างข้อความตามภาษาที่ต้องการ
          const negativePhrase = getRandomPhrase('negative');
          
          if (language === 'thai' && isEnglishNoDataResponse) {
            // กรณีข้อความตอบเป็นภาษาอังกฤษแต่ต้องการภาษาไทย
            enhancedResponse = `${negativePhrase} ไม่พบข้อมูลที่คุณต้องการในระบบ`;
          } else if (language === 'english' && isThaiNoDataResponse) {
            // กรณีข้อความตอบเป็นภาษาไทยแต่ต้องการภาษาอังกฤษ
            enhancedResponse = `${negativePhrase} We couldn't find the information you're looking for.`;
          } else {
            // กรณีภาษาของข้อความตอบตรงกับภาษาที่ต้องการ
            enhancedResponse = `${negativePhrase} ${response.response}`;
          }
        } else {
          // กรณีเป็นข้อความทั่วไป ตรวจสอบว่าภาษาตรงกับที่ต้องการหรือไม่
          const hasThaiChars = /[\u0E00-\u0E7F]/.test(response.response);
          
          if (language === 'english' && hasThaiChars) {
            // ข้อความเป็นภาษาไทยแต่ต้องการภาษาอังกฤษ
            // ส่งกลับข้อความทั่วไปที่เป็นภาษาอังกฤษ
            enhancedResponse = `I apologize, but I'm not able to fully translate the response. Here's what I can tell you: ${response.response}`;
          } else if (language === 'thai' && !hasThaiChars) {
            // ข้อความเป็นภาษาอังกฤษแต่ต้องการภาษาไทย
            enhancedResponse = `ขออภัย ฉันไม่สามารถแปลคำตอบได้ทั้งหมด นี่คือสิ่งที่ฉันบอกคุณได้: ${response.response}`;
          } else {
            // ภาษาตรงกับที่ต้องการ
            enhancedResponse = response.response;
          }
        }
      }
      
      const assistantMessage: Message = {
        type: "assistant",
        content: enhancedResponse,
        timestamp: new Date(),
        properties: response.properties
      };

      setMessages((prev) => [...prev, assistantMessage]);
      
      // เพิ่มข้อความ AI ลงใน local state (useChats) ด้วย
      if (chatRoomId) {
        addMessageToChat(chatRoomId, {
          role: "assistant",
          content: enhancedResponse,
          timestamp: Date.now(),
          properties: response.properties
        });
        
        // บันทึกข้อความทั้งหมดลงฐานข้อมูล
        const chatSession = getChatSession(chatRoomId);
        if (chatSession) {
          const messagesForDB = chatSession.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            properties: msg.properties
          }));
          
          console.log(language === 'thai' 
            ? "กำลังบันทึกประวัติการสนทนาลงฐานข้อมูล:" 
            : "Saving chat history to database:", chatRoomId, 
            language === 'thai' ? messagesForDB.length + " ข้อความ" : messagesForDB.length + " messages");
          
          // เพิ่มการป้องกันความล้มเหลวในการบันทึกประวัติโดยใช้ setTimeout เพื่อไม่ให้กระทบกับ UX
          setTimeout(async () => {
            try {
              // บันทึกลงฐานข้อมูลผ่าน API
              const saved = await saveChatHistory(chatRoomId, messagesForDB);
              if (saved) {
                console.log(language === 'thai' ? "บันทึกประวัติการสนทนาสำเร็จ" : "Chat history saved successfully");
              } else {
                console.warn(language === 'thai' 
                  ? "ไม่สามารถบันทึกประวัติการสนทนาลงฐานข้อมูลได้" 
                  : "Unable to save chat history to database");
                // แสดง toast แบบ silent ไม่รบกวนการใช้งาน
                toast.info(translate(
                  "ประวัติการสนทนาถูกบันทึกเฉพาะในเบราว์เซอร์",
                  "Chat history is stored only in your browser",
                  language
                ), {
                  duration: 3000,
                });
              }
            } catch (error) {
              console.error(language === 'thai' 
                ? "เกิดข้อผิดพลาดในการบันทึกประวัติการสนทนา:" 
                : "Error saving chat history:", error);
              // ไม่แสดง toast เพื่อไม่รบกวนผู้ใช้
            }
          }, 500); // รอเวลาเล็กน้อยเพื่อไม่ให้กระทบกับการแสดงผลหลัก
        }
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error(translate(
        errorMessages.serverError.thai,
        errorMessages.serverError.english,
        language
      ));
    } finally {
      setIsLoading(false);
    }
  };

  // Function to handle image loading errors
  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    e.currentTarget.style.display = 'none';
    const errorPlaceholder = e.currentTarget.parentElement?.querySelector('.image-error-placeholder');
    if (errorPlaceholder) {
      errorPlaceholder.classList.remove('hidden');
    }
  };

  // Display property information in a more structured way
  const renderPropertyCard = (property: Record<string, string>, index: number) => {
    const hasImage = property["รูป"] && property["รูป"] !== "ไม่มี";
    
    return (
      <div key={index} className="bg-white dark:bg-slate-800 rounded-lg p-3 mb-2 shadow-sm border border-#43BE98/20">
        {property["โครงการ"] && (
          <div className="font-medium text-#43BE98">{property["โครงการ"]}</div>
        )}
        <div className="grid grid-cols-2 gap-2 mt-1 text-sm">
          {property["ประเภท"] && (
            <div><span className="text-slate-500">{translate("ประเภท", "Type", language)}:</span> {property["ประเภท"]}</div>
          )}
          {property["ราคา"] && (
            <div><span className="text-slate-500">{translate("ราคา", "Price", language)}:</span> {property["ราคา"]} {translate("บาท", "THB", language)}</div>
          )}
          {property["รูปแบบ"] && (
            <div><span className="text-slate-500">{translate("รูปแบบ", "Style", language)}:</span> {property["รูปแบบ"]}</div>
          )}
          {property["ตำแหน่ง"] && property["ตำแหน่ง"] !== "ไม่มี" && (
            <div><span className="text-slate-500">{translate("ตำแหน่ง", "Location", language)}:</span> {property["ตำแหน่ง"]}</div>
          )}
        </div>

        {/* Image section with better error handling */}
        {hasImage && (
          <div className="mt-3 relative rounded-md overflow-hidden bg-gray-100 dark:bg-gray-700 aspect-video">
            <img 
              src={property["รูป"]} 
              alt={property["โครงการ"] || "Property"} 
              className="w-full h-full object-cover transition-opacity duration-300 hover:opacity-95"
              onError={handleImageError}
              loading="lazy"
            />
            <div className="image-error-placeholder hidden absolute inset-0 flex flex-col items-center justify-center text-gray-400">
              <ImageOff className="h-8 w-8 mb-2" />
              <span className="text-xs">{translate("ไม่สามารถโหลดรูปได้", "Could not load image", language)}</span>
            </div>
          </div>
        )}

        {/* Amenities section - showing nearby facilities */}
        <div className="mt-2 text-sm grid grid-cols-2 gap-x-2 gap-y-1">
          {property["สถานศึกษา"] && property["สถานศึกษา"] !== "ไม่มี" && (
            <div><span className="text-slate-500">{translate("สถานศึกษา", "Educational Institution", language)}:</span> {property["สถานศึกษา"]}</div>
          )}
          {property["สถานีรถไฟฟ้า"] && property["สถานีรถไฟฟ้า"] !== "ไม่มี" && (
            <div><span className="text-slate-500">{translate("สถานีรถไฟฟ้า", "Mass Transit", language)}:</span> {property["สถานีรถไฟฟ้า"]}</div>
          )}
          {property["ห้างสรรพสินค้า"] && property["ห้างสรรพสินค้า"] !== "ไม่มี" && (
            <div><span className="text-slate-500">{translate("ห้างสรรพสินค้า", "Shopping Mall", language)}:</span> {property["ห้างสรรพสินค้า"]}</div>
          )}
          {property["โรงพยาบาล"] && property["โรงพยาบาล"] !== "ไม่มี" && (
            <div><span className="text-slate-500">{translate("โรงพยาบาล", "Hospital", language)}:</span> {property["โรงพยาบาล"]}</div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(85vh-90px)]">
      <Card className="flex-1 overflow-hidden flex flex-col border-[#43BE98]">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`chat-message ${
                message.type === "user" ? "user-message" : "assistant-message"
              }`}
            >
              <div className="flex items-start">
                {message.type === "assistant" && (
                  <div className="mr-2 flex-shrink-0 rounded-full bg-[#43BE98] p-1">
                    <img 
  src="/src/image/FundeeDAO.png" 
  alt="AI" 
  className="h-8 w-8 rounded-full" 
/>
                  </div>
                )}
                <div className="max-w-[85%]">
                  <div className="text-sm font-medium">
                    {message.type === "user" 
                      ? translate("คุณ", "You", language) 
                      : "Property AI Guru"}
                  </div>
                  <div className="mt-1 whitespace-pre-line">{message.content}</div>
                  
                  {/* Render properties if available */}
                  {message.properties && message.properties.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {message.properties.map((property, propIndex) => 
                        renderPropertyCard(property, propIndex)
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="text-xs text-white mt-1 text-right">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={handleSubmit} className="p-4 border-t border-#43BE98/20 flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={translate("พิมพ์ข้อความของคุณที่นี่...", "Type your message here...", language)}
            disabled={isLoading}
            className="flex-1 border-[#43BE98] focus-visible:ring-#43BE98/50"
          />
          <Button 
            type="submit" 
            disabled={isLoading || !inputValue.trim()}
            className="bg-[#43BE98] hover:bg-#43BE98/90"
          >
            {isLoading ? <Loader className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </Card>
    </div>
  );
}
