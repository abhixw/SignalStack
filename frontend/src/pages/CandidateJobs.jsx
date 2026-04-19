import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Briefcase, ChevronRight, Activity, ArrowLeft } from 'lucide-react';
import { getCandidateJobs } from '../api';

export default function CandidateJobs() {
    const [jobs, setJobs] = useState([]);
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

        async function loadJobs() {
            try {
                const data = await getCandidateJobs();
                setJobs(data);
            } catch (error) {
                console.error("Failed to load jobs", error);
            } finally {
                setLoading(false);
            }
        }
        loadJobs();
    }, [navigate]);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">Available Job Postings</h1>
                    <p className="mt-1 text-sm text-gray-500">Welcome, <span className="font-semibold text-indigo-600">{candidateId}</span>. Browse and apply to active roles.</p>
                </div>
                <Link
                    to="/candidate/applications"
                    className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    My Applications
                </Link>
            </div>

            {loading ? (
                <div className="text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-indigo-500 border-t-transparent"></div>
                    <p className="mt-2 text-gray-500">Loading jobs...</p>
                </div>
            ) : jobs.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed border-gray-300">
                    <Briefcase className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No active job postings</h3>
                    <p className="mt-1 text-sm text-gray-500">Check back later for new opportunities.</p>
                </div>
            ) : (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {jobs.map((job) => (
                        <div key={job.id} className="bg-white overflow-hidden shadow rounded-lg border border-gray-200 flex flex-col">
                            <div className="px-4 py-5 sm:p-6 flex-grow">
                                <div className="flex items-center mb-4">
                                    <div className="h-10 w-10 rounded-full bg-indigo-100 flex items-center justify-center">
                                        <Briefcase className="h-5 w-5 text-indigo-600" />
                                    </div>
                                    <div className="ml-3">
                                        <h3 className="text-lg font-medium text-gray-900">{job.title}</h3>
                                    </div>
                                </div>
                                <p className="text-sm text-gray-500 line-clamp-3 mb-4">{job.description}</p>
                                <div className="flex flex-wrap gap-2">
                                    {job.tasks.slice(0, 3).map((task, index) => (
                                        <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                            {task.title}
                                        </span>
                                    ))}
                                    {job.tasks.length > 3 && (
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                                            +{job.tasks.length - 3} more
                                        </span>
                                    )}
                                </div>
                            </div>
                            <div className="bg-gray-50 px-4 py-4 sm:px-6">
                                <Link
                                    to={`/submit-proof/${job.id}?candidateId=${candidateId}`}
                                    className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
                                >
                                    Apply Now
                                    <ChevronRight className="ml-1 h-4 w-4" />
                                </Link>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
