import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FileText, CheckCircle, Clock, AlertCircle, ArrowLeft, Trophy } from 'lucide-react';
import { getCandidateApplications } from '../api';

export default function CandidateApplications() {
    const [applications, setApplications] = useState([]);
    const [loading, setLoading] = useState(true);
    const [candidateId, setCandidateId] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const storedId = localStorage.getItem('candidateId');
        if (!storedId) {
            navigate('/candidate');
            return;
        }
        setCandidateId(storedId);

        async function loadApplications() {
            try {
                const data = await getCandidateApplications(storedId);
                setApplications(data);
            } catch (error) {
                console.error("Failed to load applications", error);
            } finally {
                setLoading(false);
            }
        }
        loadApplications();
    }, [navigate]);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8 flex items-center">
                <Link to="/candidate/jobs" className="mr-4 p-2 rounded-full hover:bg-gray-100 transition-colors">
                    <ArrowLeft className="h-6 w-6 text-gray-500" />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">My Applications</h1>
                    <p className="mt-1 text-sm text-gray-500">Track your progress and view evaluation results.</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading your applications...</p>
                </div>
            ) : applications.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <FileText className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No applications yet</h3>
                    <p className="mt-1 text-sm text-gray-500">You haven't applied to any jobs. Go to the jobs list to get started!</p>
                    <div className="mt-6">
                        <Link
                            to="/candidate/jobs"
                            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
                        >
                            Browse Jobs
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="bg-white shadow overflow-hidden sm:rounded-md border border-gray-200">
                    <ul className="divide-y divide-gray-200">
                        {applications.map((app, index) => (
                            <li key={index} className="px-4 py-6 sm:px-6">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center">
                                        <div className={`h-12 w-12 rounded-lg flex items-center justify-center mr-4 ${app.status === 'Evaluated' ? 'bg-green-100' : 'bg-yellow-100'}`}>
                                            {app.status === 'Evaluated' ? (
                                                <Trophy className="h-6 w-6 text-green-600" />
                                            ) : (
                                                <Clock className="h-6 w-6 text-yellow-600" />
                                            )}
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-medium text-gray-900">{app.job_title}</h3>
                                            <div className="flex items-center mt-1 text-sm text-gray-500">
                                                <span>Applied on: {new Date(app.applied_at).toLocaleDateString()}</span>
                                                <span className="mx-2">•</span>
                                                <span className={`flex items-center font-medium ${app.status === 'Evaluated' ? 'text-green-600' : 'text-yellow-600'}`}>
                                                    {app.status === 'Evaluated' ? (
                                                        <CheckCircle className="h-4 w-4 mr-1" />
                                                    ) : (
                                                        <Clock className="h-4 w-4 mr-1" />
                                                    )}
                                                    {app.status}
                                                </span>
                                            </div>
                                        </div>
                                    </div>

                                    {app.status === 'Evaluated' && (
                                        <div className="text-right">
                                            <div className="text-sm text-gray-500 mb-1">Evaluation Score</div>
                                            <div className="inline-flex items-center px-3 py-1 rounded-full text-xl font-bold bg-green-50 text-green-700 border border-green-200">
                                                {(app.score * 100).toFixed(0)}%
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {app.status === 'Pending' && (
                                    <div className="mt-4 p-4 bg-gray-50 rounded-md border border-gray-100">
                                        <div className="flex">
                                            <AlertCircle className="h-5 w-5 text-gray-400 mr-2" />
                                            <p className="text-sm text-gray-600">Your application is in queue. The recruiter will trigger the AI evaluation soon. Check back later for your score!</p>
                                        </div>
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
